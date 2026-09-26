from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_serializer


def _as_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; they are always stored in UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class OverviewResponse(BaseModel):
    total_queries: int = Field(description="All recorded AI queries")
    successful_queries: int = Field(description="Queries that returned an answer")
    failed_queries: int = Field(description="Queries whose answer generation failed")
    success_rate: float = Field(description="Percentage of successful queries (0-100)")
    avg_latency_ms: int = Field(description="Mean end-to-end latency in milliseconds")
    retrieved_documents_total: int = Field(
        description="Sum of documents retrieved across queries"
    )
    unique_users: int = Field(description="Distinct users who asked queries")


class DailyPoint(BaseModel):
    date: str = Field(description="UTC day (YYYY-MM-DD)")
    queries: int = Field(description="Queries that day")
    successful: int = Field(description="Successful queries that day")
    failed: int = Field(description="Failed queries that day")
    avg_latency_ms: int = Field(description="Mean latency that day")


class DailyResponse(BaseModel):
    days: list[DailyPoint] = Field(description="One point per UTC day, oldest first")


class TopDocumentItem(BaseModel):
    document: str = Field(description="Source document filename")
    count: int = Field(description="Number of queries citing this document")


class TopDocumentsResponse(BaseModel):
    documents: list[TopDocumentItem] = Field(
        description="Most cited documents, most cited first"
    )


class TopQueryItem(BaseModel):
    query: str = Field(description="Search text as typed")
    count: int = Field(description="Number of times this query was asked")


class TopQueriesResponse(BaseModel):
    queries: list[TopQueryItem] = Field(description="Most frequent queries first")


class RecentSearchItem(BaseModel):
    id: str
    query: str
    success: bool
    latency_ms: int
    retrieved_documents: int
    created_at: datetime = Field(description="When the query ran (UTC)")

    @field_serializer("created_at")
    def _serialize_datetime(self, value: datetime) -> datetime:
        return _as_utc(value)


class RecentSearchesResponse(BaseModel):
    searches: list[RecentSearchItem] = Field(
        description="Most recent queries, newest first"
    )
