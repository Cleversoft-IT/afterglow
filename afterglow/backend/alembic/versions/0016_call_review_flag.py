"""call review_flag column (round-10: agentic pipeline)

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-18

The agentic post-call pipeline can mark a Call as needing human review
either explicitly (agent invokes the `flag_for_review` tool) or implicitly
(loop exits via `max_turns` without finalize). The orchestrator stores the
reason in `Call.review_flag` as JSONB:

    {
      "reason": "agent_did_not_finalize" | "<agent text>",
      "severity": "low" | "medium" | "high",
      "turn_count": <int, optional>,
      "flagged_by": "agent" | "system"
    }

`calls.status` is intentionally NOT constrained at the DB level — `0001_init`
declared it as a free-text `String(30)`, so the new `'needs_review'` value is
already accepted. No CHECK constraint to amend.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "calls",
        sa.Column("review_flag", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("calls", "review_flag")
