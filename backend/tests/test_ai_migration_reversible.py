import pytest
from alembic.config import Config
from alembic import command


def test_migration_0011_upgrade_and_downgrade():
    alembic_cfg = Config("backend/alembic.ini")
    alembic_cfg.set_main_option("script_location", "backend/alembic")
    # Upgrade to head
    command.upgrade(alembic_cfg, "head")
    # Downgrade back to 0010
    command.downgrade(alembic_cfg, "0010_add_soft_delete")
    # Re-upgrade to head
    command.upgrade(alembic_cfg, "head")
