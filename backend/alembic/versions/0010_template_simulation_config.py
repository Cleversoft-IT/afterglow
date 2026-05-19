"""templates.simulation_config JSONB — per-template demo recording.

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-16

A template that is not one of the bundled seeds (restaurant/dentist/bodyshop)
has no demo MP3 by default. The Simulator screen needs to know whether a
playable recording exists for the active template, and where to fetch it.

`simulation_config` shape:
  {
    "caller_name": "Mark",                       # display name on the dialer
    "caller_phone_e164": "+15551112233",         # phone used at submit time
    "script_turns": [                            # ordered list of TTS lines
      {"speaker": "operator|caller", "voice": "sarah", "text": "..."}
    ],
    "audio_url": "/var/data/audio/templates/<id>.mp3",
    "audio_status": "pending|ready|failed",
    "audio_generated_at": "2026-05-16T...",
    "audio_source": "tts_generated|user_uploaded|bundled"
  }

`None` means "no simulation config — use the bundled demo MP3 if the
template is a seed, else block the Simulator and ask the user to generate
or upload one".
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "templates",
        sa.Column("simulation_config", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("templates", "simulation_config")
