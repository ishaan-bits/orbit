import pytest

from app.services.auth import ensure_rbac_seed


@pytest.fixture()
def rbac_seed(db_session):
    """Seed default roles and the General folder into the test database."""
    ensure_rbac_seed(db_session)
    return db_session
