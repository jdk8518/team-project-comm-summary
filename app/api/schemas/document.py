"""
app/api/schemas/document.py
Pydantic 스키마 레이어 — app.schemas의 re-export 래퍼.
순환 임포트 방지를 위해 app.schemas가 정규 정의를 보유하고,
이 모듈은 외부에서 app.api.schemas.document 경로로 접근 시 동일한 클래스를 노출합니다.
"""
from app.schemas import *  # noqa: F401, F403
from app.schemas import (
    DocumentUploadData, UploadResponse,
    Section, StructuredContent, ExtractionMetadata, ExtractionData, ExtractResponse,
    CoreStructure, KeySentence, KeyKeywords, VerificationCandidate, EvidenceGrounding,
    AnalysisData, AnalyzeResponse,
    MainContentItem, SummaryResult, SummaryData, SummarizeResponse,
    ValidationIssueItem, HumanChecklistItem, ValidationResult, ValidationData, ValidateResponse,
    ArchivingInfo, DocumentInfo, IntegratedResultData, IntegratedResultResponse,
    SaveDocumentRequest, SaveDocumentResponse,
    DepartmentListResponse, SearchItem, SearchResponse,
    SummaryUpdateRequest, DocumentResultsUpdate,
    MoveFileRequest, MoveFileResponse,
    FolderRecommendItem, FolderRecommendResponse, FolderRecommendRequest,
    UnconfirmedDocumentItem, UnconfirmedListResponse,
    ConfirmDocumentRequest, BatchConfirmItem, BatchConfirmRequest, BatchDeleteRequest,
)
