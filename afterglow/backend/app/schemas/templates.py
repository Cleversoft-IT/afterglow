"""Pydantic schemas for template configuration + prompt-to-template wizard."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class FieldDefinition(BaseModel):
    key: str
    type: str
    label: str
    required: bool = False
    sensitive: bool = False
    options: list[str] = Field(default_factory=list)
    description: Optional[str] = None


class ActionDefinition(BaseModel):
    key: str
    label: str
    execution_mode: str = "auto"  # 'auto' | 'manual-only'
    mock_target: str = "generic"
    description: Optional[str] = None


class TemplateView(BaseModel):
    id: UUID
    name: str
    version: int
    description: Optional[str] = None
    domain_hint: str = "generic"
    fields_schema: list[FieldDefinition] = Field(default_factory=list)
    action_types: list[ActionDefinition] = Field(default_factory=list)
    custom_dictionary: list[str] = Field(default_factory=list)
    prompt_hints: Optional[str] = None
    is_active: bool = False
    created_at: datetime


class TemplateWizardRequest(BaseModel):
    description: str = Field(min_length=20)
    language: str = "it"


class TemplateWizardResponse(BaseModel):
    name: str
    description: str
    fields_schema: list[FieldDefinition]
    action_types: list[ActionDefinition]
    custom_dictionary: list[str]
    prompt_hints: str
