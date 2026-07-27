from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class SavePreviewRequest(BaseModel):
    document_type: str = Field(..., description="회의록, 공문, 보고서 중 최종 선택값")
    reference_date: date | None = None


class SaveResultRequest(SavePreviewRequest):
    review_confirmed: bool = False
    user_confirmed: bool = False


class AnalyzeRequest(BaseModel):
    categories: list[str] = Field(default_factory=lambda: ["회의록", "공문", "보고서", "공고문"])


class FolderDocument(BaseModel):
    file_name: str
    file_type: str
    file_size: int
    modified_date: str


class FolderDocumentListResponse(BaseModel):
    folder_path: str
    documents: list[FolderDocument]


class AnalysisResponse(BaseModel):
    document_id: str
    status: str
    document: dict[str, Any]
    analysis: dict[str, Any]
    summary: dict[str, Any]


class VerificationRequest(BaseModel):
    document_id: str | None = Field(default=None, description="추출·분석·요약을 완료한 문서 식별자")
    source_text: str | None = None
    analysis: dict[str, Any] | None = None
    summary: dict[str, Any] | None = None


class VerificationIssue(BaseModel):
    category: str
    reason: str
    source_evidence: list[str]
    human_check: str


class VerificationResponse(BaseModel):
    passed: bool
    issues: list[VerificationIssue]
    revision_instruction: str


class TextExtractionResponse(BaseModel):
    document_id: str
    file_name: str
    file_type: str
    file_size: int
    reference_date: str
    reference_date_source: str
    text_length: int
    text_preview: str
    extraction_status: str = "EXTRACTED"
