"""initial autoresearch schema

Revision ID: 20260629_0001
Revises:
Create Date: 2026-06-29
"""

from __future__ import annotations

from alembic import op

revision = "20260629_0001"
down_revision = None
branch_labels = None
depends_on = None

STATUS_CHECK = """
CHECK (status IN (
    'planned','queued','claimed','running','completed','failed','rejected','superseded','blocked','degraded','archived'
))
"""


def _json_table(name: str, *, status: bool = True) -> None:
    status_column = "status TEXT NOT NULL DEFAULT 'planned'," if status else ""
    status_constraint = f", CONSTRAINT ck_{name}_status {STATUS_CHECK}" if status else ""
    op.execute(
        f"""
        CREATE TABLE {name} (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '',
            {status_column}
            payload JSONB NOT NULL DEFAULT '{{}}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            {status_constraint}
        );
        """
    )


def upgrade() -> None:
    _json_table("research_sources", status=False)
    _json_table("research_insights", status=False)
    _json_table("research_hypotheses")
    _json_table("research_programs")
    _json_table("research_questions")
    _json_table("method_cards")
    _json_table("protocols")
    _json_table("research_intake_items")
    _json_table("research_sessions")
    _json_table("research_rounds")
    _json_table("research_events", status=False)
    _json_table("research_experiments")
    _json_table("research_artifacts", status=False)
    _json_table("benchmarks")
    _json_table("benchmark_runs")
    _json_table("evidence_records")
    _json_table("reviews")
    _json_table("decisions")
    _json_table("experiences")
    _json_table("experience_topics", status=False)
    _json_table("logs", status=False)
    _json_table("log_topics", status=False)

    op.execute("CREATE INDEX idx_research_intake_items_status ON research_intake_items(status);")
    op.execute("CREATE INDEX idx_research_programs_status ON research_programs(status);")
    op.execute("CREATE INDEX idx_research_questions_status ON research_questions(status);")
    op.execute("CREATE INDEX idx_method_cards_status ON method_cards(status);")
    op.execute("CREATE INDEX idx_protocols_status ON protocols(status);")
    op.execute("CREATE INDEX idx_research_sessions_status ON research_sessions(status);")
    op.execute("CREATE INDEX idx_research_rounds_status ON research_rounds(status);")
    op.execute("CREATE INDEX idx_research_experiments_status ON research_experiments(status);")
    op.execute("CREATE INDEX idx_benchmark_runs_status ON benchmark_runs(status);")
    op.execute("CREATE INDEX idx_evidence_records_status ON evidence_records(status);")
    op.execute("CREATE INDEX idx_reviews_status ON reviews(status);")
    op.execute("CREATE INDEX idx_decisions_status ON decisions(status);")
    op.execute("CREATE INDEX idx_experiences_status ON experiences(status);")


def downgrade() -> None:
    for table in [
        "log_topics",
        "logs",
        "experience_topics",
        "experiences",
        "decisions",
        "reviews",
        "evidence_records",
        "benchmark_runs",
        "benchmarks",
        "research_artifacts",
        "research_experiments",
        "research_events",
        "research_rounds",
        "research_sessions",
        "research_intake_items",
        "protocols",
        "method_cards",
        "research_questions",
        "research_programs",
        "research_hypotheses",
        "research_insights",
        "research_sources",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
