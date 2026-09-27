import json
from pathlib import Path
from typing import Any, Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings as app_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.rag import bm25, generator, reranker, retriever
from app.rag.generator import GenerationError, Passage
from app.rag.retriever import Candidate
from app.services.storage import get_uploads_dir

# --- fixtures ---------------------------------------------------------------


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session = testing_session()
    yield session
    session.close()


@pytest.fixture()
def uploads_dir(tmp_path: Path) -> Path:
    path = tmp_path / "uploads"
    path.mkdir()
    return path


@pytest.fixture()
def chroma_dir(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / "chroma_db"
    monkeypatch.setattr(app_settings, "chroma_path", str(path))
    return path


@pytest.fixture()
def fake_embedder(monkeypatch) -> None:
    def _encode(texts):
        return [
            [float(len(text)), float(sum(ord(c) for c in text) % 101), 1.0]
            for text in texts
        ]

    monkeypatch.setattr("app.rag.embedder.encode_texts", _encode)


@pytest.fixture()
def fake_reranker(monkeypatch) -> None:
    class FakeCrossEncoder:
        def predict(self, pairs):
            return [float(len(text)) for _query, text in pairs]

    monkeypatch.setattr(reranker, "get_model", lambda: FakeCrossEncoder())


@pytest.fixture()
def fake_generator(monkeypatch) -> None:
    monkeypatch.setattr(
        generator, "generate_answer", lambda query, passages: "**Hello** world"
    )
    monkeypatch.setattr(
        generator,
        "stream_answer",
        lambda query, passages: iter(["**Hello** ", "world"]),
    )


@pytest.fixture()
def client(
    db_session,
    uploads_dir: Path,
    chroma_dir: Path,
    fake_embedder,
    fake_reranker,
    fake_generator,
    rbac_seed,
):
    testing_session = sessionmaker(
        bind=db_session.get_bind(),
        autoflush=False,
        expire_on_commit=False,
    )

    def _override_get_db():
        # mirror production: fresh session per request so relationship
        # caches are never shared between requests
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_uploads_dir] = lambda: uploads_dir

    with TestClient(app, base_url="https://testserver") as test_client:
        response = test_client.post(
            "/api/auth/register",
            json={"email": "admin@orbit.test", "password": "password123"},
        )
        assert response.status_code == 201, response.text
        yield test_client

    app.dependency_overrides.clear()


# --- helpers ----------------------------------------------------------------


def upload_file(
    client: TestClient,
    filename: str,
    content: bytes,
    content_type: str = "text/plain",
) -> dict[str, Any]:
    response = client.post(
        "/api/documents/upload",
        files={"file": (filename, content, content_type)},
    )
    assert response.status_code == 201, response.text
    return response.json()


def make_pdf_bytes(pages: list[str]) -> bytes:
    import pymupdf

    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    payload = doc.tobytes()
    doc.close()
    return payload


def index(client: TestClient, document_id: str) -> dict[str, Any]:
    response = client.post(f"/api/documents/{document_id}/index")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "indexed", payload
    return payload


def seed_text_document(client: TestClient, name: str, content: str) -> dict[str, Any]:
    document = upload_file(client, name, content.encode())
    index(client, document["id"])
    return document


def ask(client: TestClient, query: str, conversation_id: Optional[str] = None):
    body: dict[str, Any] = {"query": query}
    if conversation_id:
        body["conversation_id"] = conversation_id
    return client.post("/api/chat/query", json=body)


# --- chat query -------------------------------------------------------------


def test_query_returns_answer_and_sources(client: TestClient) -> None:
    document = seed_text_document(
        client, "HR Handbook.txt", "Employees enjoy a vacation policy of twenty days."
    )

    response = ask(client, "What is the vacation policy?")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["answer"] == "**Hello** world"
    assert payload["conversation_id"]
    assert payload["sources"] == [
        {
            "document": "HR Handbook.txt",
            "page": 1,
            "document_id": document["id"],
            "score": 1.0,
        }
    ]


def test_query_sources_reference_pdf_pages(client: TestClient) -> None:
    pdf = make_pdf_bytes(
        ["Leave policy: twenty days per year.", "Expense rules: submit receipts."]
    )
    document = upload_file(client, "Policies.pdf", pdf, "application/pdf")
    index(client, document["id"])

    payload = ask(client, "How many leave days do employees get?").json()

    assert payload["answer"] == "**Hello** world"
    assert payload["sources"] == [
        {
            "document": "Policies.pdf",
            "page": 1,
            "document_id": document["id"],
            "score": 1.0,
        },
        {
            "document": "Policies.pdf",
            "page": 2,
            "document_id": document["id"],
            "score": 1.0,
        },
    ]


def test_query_continues_conversation(client: TestClient) -> None:
    seed_text_document(client, "guide.txt", "The guide explains onboarding steps.")

    first = ask(client, "What is onboarding?").json()
    second = ask(client, "Tell me more", conversation_id=first["conversation_id"])

    assert second.status_code == 200
    assert second.json()["conversation_id"] == first["conversation_id"]

    history = client.get("/api/chat/history").json()
    assert len(history["conversations"]) == 1
    conversation = history["conversations"][0]
    assert [m["role"] for m in conversation["messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


def test_query_unknown_conversation_returns_404(client: TestClient) -> None:
    response = ask(client, "hello", conversation_id="missing-id")
    assert response.status_code == 404


def test_query_blank_returns_422(client: TestClient) -> None:
    response = client.post("/api/chat/query", json={"query": "   "})
    assert response.status_code == 422


def test_query_without_documents_skips_gemini(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        generator,
        "generate_answer",
        lambda *args: pytest.fail("Gemini must not be called"),
    )

    payload = ask(client, "What is the leave policy?").json()

    assert "no indexed documents" in payload["answer"]
    assert payload["sources"] == []

    history = client.get("/api/chat/history").json()
    assistant = history["conversations"][0]["messages"][1]
    assert assistant["role"] == "assistant"
    assert assistant["sources"] == []


def test_query_generation_error_returns_502(client: TestClient, monkeypatch) -> None:
    seed_text_document(client, "notes.txt", "Some indexed notes content.")

    def _explode(query, passages):
        raise GenerationError("GEMINI_API_KEY is not configured")

    monkeypatch.setattr(generator, "generate_answer", _explode)

    response = ask(client, "What is in the notes?")

    assert response.status_code == 502
    assert response.json()["detail"] == "GEMINI_API_KEY is not configured"

    # the user message is kept, but no assistant answer is stored
    history = client.get("/api/chat/history").json()
    roles = [m["role"] for m in history["conversations"][0]["messages"]]
    assert roles == ["user"]


def test_query_stream_sends_sse_and_persists(client: TestClient) -> None:
    document = seed_text_document(
        client, "faq.txt", "Frequently asked questions content."
    )

    response = client.post(
        "/api/chat/query",
        json={"query": "What is the FAQ about?"},
        headers={"Accept": "text/event-stream"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: sources" in body
    assert "event: token" in body
    assert "**Hello** " in body
    assert "event: done" in body
    assert '"conversation_id"' in body

    history = client.get("/api/chat/history").json()
    messages = history["conversations"][0]["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[1]["content"] == "**Hello** world"
    assert messages[1]["sources"] == [
        {
            "document": "faq.txt",
            "page": 1,
            "document_id": document["id"],
            "score": 1.0,
        }
    ]


def test_query_stream_without_documents_still_streams(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(
        generator,
        "stream_answer",
        lambda *args: pytest.fail("Gemini must not be called"),
    )

    response = client.post(
        "/api/chat/query",
        json={"query": "Anything indexed?"},
        headers={"Accept": "text/event-stream"},
    )

    assert response.status_code == 200
    assert "event: done" in response.text
    assert "no indexed documents" in response.text


def test_query_stream_reports_generation_error(client: TestClient, monkeypatch) -> None:
    seed_text_document(client, "doc.txt", "Indexed document content here.")

    def _explode(query, passages):
        raise GenerationError("Gemini is unavailable")

    monkeypatch.setattr(generator, "stream_answer", _explode)

    response = client.post(
        "/api/chat/query",
        json={"query": "Question?"},
        headers={"Accept": "text/event-stream"},
    )

    assert response.status_code == 200
    assert "event: error" in response.text
    assert "Gemini is unavailable" in response.text


# --- history ----------------------------------------------------------------


def test_history_returns_empty_list(client: TestClient) -> None:
    response = client.get("/api/chat/history")
    assert response.status_code == 200
    assert response.json() == {"conversations": []}


def test_history_orders_conversations_by_activity(client: TestClient) -> None:
    seed_text_document(client, "a.txt", "content about apples and pears")
    ask(client, "First question")
    ask(client, "Second question")

    history = client.get("/api/chat/history").json()

    assert len(history["conversations"]) == 2
    assert history["conversations"][0]["title"] == "Second question"
    assert len(history["conversations"][0]["messages"]) == 2
    first = history["conversations"][1]
    assert first["title"] == "First question"
    assert len(first["messages"]) == 2


def test_history_messages_carry_timestamps(client: TestClient) -> None:
    seed_text_document(client, "b.txt", "content")
    ask(client, "Question?")

    conversation = client.get("/api/chat/history").json()["conversations"][0]
    for message in conversation["messages"]:
        assert message["created_at"]
        assert message["id"]


# --- bm25 -------------------------------------------------------------------


def test_bm25_tokenize() -> None:
    assert bm25.tokenize("Vacation Policy v2!") == ["vacation", "policy", "v2"]


def test_bm25_ranks_matching_documents_higher() -> None:
    index = bm25.build_index(
        ["c0", "c1", "c2"],
        [
            "vacation policy gives twenty days off",
            "expense reimbursement requires receipts",
            "onboarding checklist for new employees",
        ],
    )

    results = index.search("vacation days")

    assert results
    assert results[0][0] == "c0"
    assert all(score > 0 for _chunk_id, score in results)


def test_bm25_empty_query_and_empty_index() -> None:
    index = bm25.build_index([], [])
    assert index.search("anything") == []

    filled = bm25.build_index(["c0"], ["some text"])
    assert filled.search("") == []


# --- hybrid retrieval / RRF -------------------------------------------------


def _candidate(chunk_id: str) -> Candidate:
    return Candidate(
        id=chunk_id,
        text=f"text {chunk_id}",
        document_id="doc",
        filename="file.txt",
        page=1,
        chunk_index=0,
    )


def test_rrf_merge_prefers_documents_in_both_rankings() -> None:
    dense = [_candidate("a"), _candidate("b"), _candidate("c")]
    sparse = [_candidate("c"), _candidate("d")]

    merged = retriever._rrf_merge(dense, sparse, top_k=4)

    assert [candidate.id for candidate in merged] == ["c", "a", "b", "d"]


def test_retrieve_returns_empty_for_empty_corpus(chroma_dir: Path) -> None:
    assert retriever.retrieve("anything") == []


# --- reranker ---------------------------------------------------------------


def test_reranker_picks_highest_scores(monkeypatch) -> None:
    class FakeModel:
        def predict(self, pairs):
            return [1.0, 5.0, 3.0]

    monkeypatch.setattr(reranker, "get_model", lambda: FakeModel())
    candidates = [_candidate("a"), _candidate("b"), _candidate("c")]

    result = reranker.rerank("query", candidates, top_k=3)

    assert [candidate.id for candidate in result] == ["b", "c", "a"]


def test_reranker_limits_to_top_k(monkeypatch) -> None:
    class FakeModel:
        def predict(self, pairs):
            return [float(index) for index in range(len(pairs))]

    monkeypatch.setattr(reranker, "get_model", lambda: FakeModel())
    candidates = [_candidate("a"), _candidate("b"), _candidate("c")]

    result = reranker.rerank("query", candidates, top_k=2)

    assert [candidate.id for candidate in result] == ["c", "b"]


def test_reranker_falls_back_when_model_unavailable(monkeypatch) -> None:
    def _explode():
        raise RuntimeError("model missing")

    monkeypatch.setattr(reranker, "get_model", _explode)
    candidates = [_candidate("a"), _candidate("b"), _candidate("c")]

    result = reranker.rerank("query", candidates, top_k=3)

    assert [candidate.id for candidate in result] == ["a", "b", "c"]


def test_reranker_empty_input(monkeypatch) -> None:
    monkeypatch.setattr(
        reranker,
        "get_model",
        lambda: pytest.fail("model must not load for empty input"),
    )
    assert reranker.rerank("query", []) == []


def test_reranker_loads_real_model() -> None:
    try:
        model = reranker.get_model()
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"reranker model unavailable: {exc}")

    assert model is reranker.get_model()
    scores = model.predict(
        [
            ("leave policy", "Employees get twenty days of vacation."),
            ("leave policy", "The server rack has 42 units."),
        ]
    )
    assert float(scores[0]) > float(scores[1])


# --- generator --------------------------------------------------------------


def _passage(label: int = 1) -> Passage:
    return Passage(
        label=label, filename="HR Handbook.pdf", page=14, text="Twenty days."
    )


def test_prompt_contains_context_and_question() -> None:
    prompt = generator.build_user_prompt("What is the leave policy?", [_passage()])

    assert "[1] HR Handbook.pdf — page 14" in prompt
    assert "Twenty days." in prompt
    assert "Question: What is the leave policy?" in prompt


def test_prompt_without_passages_uses_placeholder() -> None:
    prompt = generator.build_user_prompt("Q", [])
    assert "(no context)" in prompt


def test_generate_answer_requires_api_key(monkeypatch) -> None:
    monkeypatch.setattr(app_settings, "gemini_api_key", "")
    with pytest.raises(GenerationError):
        generator.generate_answer("Q", [_passage()])


def test_generate_answer_parses_response(monkeypatch) -> None:
    monkeypatch.setattr(app_settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(
        generator,
        "_post_json",
        lambda payload: {
            "candidates": [{"content": {"parts": [{"text": "The answer."}]}}]
        },
    )

    assert generator.generate_answer("Q", [_passage()]) == "The answer."


def test_generate_answer_rejects_empty_candidates(monkeypatch) -> None:
    monkeypatch.setattr(app_settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(generator, "_post_json", lambda payload: {})

    with pytest.raises(GenerationError):
        generator.generate_answer("Q", [_passage()])


def test_stream_answer_yields_tokens(monkeypatch) -> None:
    monkeypatch.setattr(app_settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(
        generator,
        "_post_sse",
        lambda payload: iter(
            [
                {"candidates": [{"content": {"parts": [{"text": "Hel"}]}}]},
                {"candidates": [{"content": {"parts": [{"text": "lo"}]}}]},
            ]
        ),
    )

    assert list(generator.stream_answer("Q", [_passage()])) == ["Hel", "lo"]


def test_extract_text_joins_parts() -> None:
    data = {
        "candidates": [
            {"content": {"parts": [{"text": "a"}, {"text": "b"}]}},
        ]
    }
    assert generator._extract_text(data) == "ab"
    assert generator._extract_text({}) == ""


def test_system_prompt_encodes_groundedness_rules() -> None:
    prompt = generator.SYSTEM_PROMPT
    assert "Answer ONLY from the provided context" in prompt
    assert "Never hallucinate" in prompt
    assert "was not found" in prompt
    assert "page N" in prompt
    assert "Markdown" in prompt


# --- end-to-end with streamed JSON payload round-trip -----------------------


def test_persisted_sources_round_trip(client: TestClient) -> None:
    pdf = make_pdf_bytes(
        ["Page one text about policies.", "Page two text about rules."]
    )
    document = upload_file(client, "Round.pdf", pdf, "application/pdf")
    index(client, document["id"])

    ask(client, "What are the policies?")

    conversation = client.get("/api/chat/history").json()["conversations"][0]
    assistant = conversation["messages"][1]
    assert assistant["sources"] == [
        {
            "document": "Round.pdf",
            "page": 1,
            "document_id": document["id"],
            "score": 1.0,
        },
        {
            "document": "Round.pdf",
            "page": 2,
            "document_id": document["id"],
            "score": 1.0,
        },
    ]
    # JSON storage must be well-formed
    assert json.dumps(assistant["sources"])
