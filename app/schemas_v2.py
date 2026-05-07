from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SupportStatus = Literal["supported", "partially_supported", "unsupported"]


class CandidateChunk(BaseModel):
    chunk_id: str = ""
    parent_chunk_id: str | None = None
    text: str = ""
    paper_name: str = ""
    filename: str | None = None
    doi: str | None = None
    title: str | None = None
    year: int | str | None = None
    page: str | int | None = None
    section: str | None = None
    is_si: bool = False
    retrieval_text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None
    hit_child_ids: list[str] = Field(default_factory=list)
    bm25_rank: int | None = None
    vector_rank: int | None = None
    rrf_score: float | None = None
    rerank_score: float | None = None


class SourceCitation(BaseModel):
    citation_id: str = ""
    source_id: str = ""
    paper_name: str = ""
    filename: str | None = None
    doi: str | None = None
    page: str | int | None = None
    section: str | None = None
    is_si: bool = False
    evidence_text: str = ""
    chunk_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClaimRecord(BaseModel):
    claim: str = ""
    support_status: SupportStatus = "unsupported"
    citation_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    evidence: list[SourceCitation] = Field(default_factory=list)
    confidence: str | None = None
    rationale: str = ""
    structured_fields: dict[str, Any] = Field(default_factory=dict)
    is_agent_analysis: bool = False
    is_agent_inference: bool = False


class FeedbackRecord(BaseModel):
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_aspects: list[str] = Field(default_factory=list)
    citation_mismatch: list[str] = Field(default_factory=list)
    mixed_paper_conditions: list[str] = Field(default_factory=list)
    need_followup_retrieval: bool = False
    followup_queries: list[str] = Field(default_factory=list)
    revision_instructions: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    max_iterations: int = 1


class SynthesisResult(BaseModel):
    query: str = ""
    answer: str = ""
    claims: list[ClaimRecord] = Field(default_factory=list)
    citations: list[SourceCitation] = Field(default_factory=list)
    structured_table: list[dict[str, Any]] = Field(default_factory=list)
    literature_analysis: str = ""
    agent_analysis: str = ""
    uncertainties: list[str] = Field(default_factory=list)
    feedback_trace: list[FeedbackRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
