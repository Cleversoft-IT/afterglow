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
        "templates",
        "customers",
        "calls",
        "extracted_fields",
        "executed_actions",
        "audit_log",
        "customer_memory_chunks",
    }
    assert expected.issubset(names), f"missing: {expected - names}"
    assert "businesses" not in names, (
        "single-tenant invariant broken: 'businesses' table reintroduced"
    )
    assert "template_versions" not in names, (
        "template_versions was dropped in migration 0007; do not reintroduce it"
    )


def test_no_business_id_columns():
    """The single-tenant refactor removed business_id from every table.

    Catches a regression where someone re-adds the FK without thinking it through.
    """
    from app.db.models import Call, Customer, Template

    for model in (Template, Customer, Call):
        cols = {c.name for c in model.__table__.columns}
        assert "business_id" not in cols, (
            f"{model.__name__} unexpectedly has a business_id column"
        )
