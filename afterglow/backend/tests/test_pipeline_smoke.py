"""Day 1 smoke test — ensures every module imports without optional deps."""
from __future__ import annotations


def test_settings_load():
    from app.config import get_settings

    s = get_settings()
    assert s.app_env in {"local", "dev", "prod"}


def test_orchestrator_imports():
    import app.agents.orchestrator  # noqa: F401


def test_db_models_metadata_has_all_tables():
    from app.db.models import Base

    names = set(Base.metadata.tables.keys())
    expected = {
        "businesses",
        "templates",
        "template_versions",
        "customers",
        "calls",
        "extracted_fields",
        "executed_actions",
        "audit_log",
        "customer_memory_chunks",
    }
    assert expected.issubset(names), f"missing: {expected - names}"
