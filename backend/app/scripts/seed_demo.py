"""Seed the NovaTech Systems demo tenant on demand.

Usage (from ``backend/``)::

    python -m app.scripts.seed_demo

Runs the same idempotent seed used on first launch when ``SEED_DEMO=true``.
Requires migrations to have been applied (``alembic upgrade head``).
"""

import json
import logging

from sqlalchemy.exc import OperationalError

from app.db.session import SessionLocal
from app.services.demo_seed import DEMO_COMPANY, DEMO_PASSWORD, ensure_demo_seed

logger = logging.getLogger("orbit.scripts.seed_demo")


def main() -> int:
    db = SessionLocal()
    try:
        created = ensure_demo_seed(db)
    except OperationalError:
        print("Database schema is missing — run `alembic upgrade head` first.")
        return 1
    except Exception:  # noqa: BLE001 - surface any seed failure to the operator
        logger.exception("demo_seed.failed")
        print("Seeding failed — see the traceback above.")
        return 1
    finally:
        db.close()

    print(
        json.dumps(
            {
                "company": DEMO_COMPANY,
                "password": DEMO_PASSWORD,
                "created": created,
                "status": "ok",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
