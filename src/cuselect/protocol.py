"""Validated research-protocol contract for the CU-001 evidence-first study.

No experimental or computed observations are generated here.
"""
from __future__ import annotations
from pathlib import Path
from typing import Literal
import json
from pydantic import BaseModel, ConfigDict, Field

class SystemScope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reaction: str
    target_product: str
    reference_surface: str
    initial_candidates: list[str] = Field(min_length=2)
    initial_alloy_model: str

class ModelBoundaries(BaseModel):
    model_config = ConfigDict(extra="forbid")
    structures_relaxed: bool = False
    adsorption_energies_computed: bool = False
    selectivity_predicted: bool = False
    operating_potential_modeled: bool = False

class EvaluationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    primary_metric: str
    secondary_metrics: list[str]
    holdout_group: str
    controls: list[str]
    evaluation_status: Literal["planned_not_run", "running", "completed"]

class ResearchProtocol(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["0.1"]
    campaign_id: Literal["CU-001"]
    research_question: str = Field(min_length=20)
    task_type: Literal["evidence_reliability"]
    system: SystemScope
    known_model_boundaries: ModelBoundaries
    evaluation: EvaluationPlan

def load_research_protocol(path: str | Path) -> ResearchProtocol:
    """Parse, validate and return the versioned protocol from disk."""
    return ResearchProtocol.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
