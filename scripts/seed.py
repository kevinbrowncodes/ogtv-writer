"""Seed the database with a demo user and sample items.

Run it with either:

    make seed
    python -m scripts.seed

Idempotent: safe to run repeatedly. Credentials come from .env
(SEED_USER_EMAIL / SEED_USER_PASSWORD).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a plain file (`python scripts/seed.py`) by putting the repo
# root on sys.path. (Not needed for `python -m scripts.seed`.)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402
from app.schemas.item import ItemCreate  # noqa: E402
from app.services import item_service, user_service  # noqa: E402

SAMPLE_ITEMS = [
    ("Welcome to your dashboard", "This is a sample item — edit or delete it.", "active"),
    ("Draft proposal", "An example with a longer description for layout testing.", "active"),
    ("Old announcement", "An archived item to show the status filter.", "archived"),
]


def main() -> None:
    settings = get_settings()
    init_db()

    with SessionLocal() as db:
        # --- Demo user --------------------------------------------------------
        if user_service.get_by_email(db, settings.seed_user_email) is None:
            user_service.create_user(
                db,
                email=settings.seed_user_email,
                password=settings.seed_user_password,
                name="Demo Admin",
                is_admin=True,
            )
            print(f"✓ Created demo user: {settings.seed_user_email}")
        else:
            print(f"• Demo user already exists: {settings.seed_user_email}")

        # --- Sample items -----------------------------------------------------
        if item_service.count_items(db) == 0:
            for title, description, status in SAMPLE_ITEMS:
                item_service.create_item(
                    db, ItemCreate(title=title, description=description, status=status)
                )
            print(f"✓ Created {len(SAMPLE_ITEMS)} sample items")
        else:
            print("• Items already present — skipping sample data")

    print("Done.")


if __name__ == "__main__":
    main()
