"""add Call.audio_diarization metadata for ASR routing

Revision ID: 0019
Revises: 0018
Create Date: 2026-05-19

Custom templates render their demo audio via Speechmatics TTS and the
resulting MP3 is STEREO (one speaker per channel). Speaker diarization
collapses synthetic mono-concat audio to a single speaker, so for those
recordings we tell Speechmatics ASR to use channel diarization instead.
The pipeline needs to know per-call which mode applies — seed templates
and user-uploaded audio stay on `"speaker"`, TTS-generated stereo
templates switch to `"channel"`. We persist this on the Call row at
submit time so the orchestrator can route the ASR call deterministically
without re-reading the template config.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "calls",
        sa.Column(
            "audio_diarization",
            sa.String(length=16),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("calls", "audio_diarization")
