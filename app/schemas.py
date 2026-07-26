"""
app/schemas.py
Pydantic 요청/응답 DTO 명세 (원본 정의 — 순환 임포트 방지)
실제 Pydantic 모델은 여기에 정의되며, app/api/schemas/document.py는 여기서 re-export합니다.
"""
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime

# 1. Upload Schemas
class DocumentUploadData(BaseModel):
    file_id: str
    file_path: str
    original_filename: str
    format: str
    mime_type: str
    size_bytes: int
    uploaded_at: str
    status: str

class UploadResponse(BaseModel):
    success: bool = True
    data: DocumentUploadData

# 2. Extract Schemas
class Section(BaseModel):
    section_id: int
    section_title: str
    content: str
    content_type: str = "paragraph"

class StructuredContent(BaseModel):
    title: str
    sections: List[Section]

class ExtractionMetadata(BaseModel):
    original_filename: str
    format: str
    extracted_char_count: int
    section_count: int
    is_analyzable: bool

class ExtractionData(BaseModel):
    file_id: str
    metadata: ExtractionMetadata
    structured_content: StructuredContent
    raw_cleaned_text: str

class ExtractResponse(BaseModel):
    success: bool = True
    data: ExtractionData

# 3. Analyze Schemas
class CoreStructure(BaseModel):
    category: str
    section_id: int
    content_summary: str

class KeySentence(BaseModel):
    sentence_id: int
    section_id: int
    text: str

class KeyKeywords(BaseModel):
    persons: List[str] = []
    organizations: List[str] = []
    schedules: List[str] = []
    metrics: List[str] = []
    concepts: List[str] = []

class VerificationCandidate(BaseModel):
    candidate_id: str
    type: str
    target: str
    display_tag: str
    evidence: str

class EvidenceGrounding(BaseModel):
    entity_or_item: str
    section_id: int
    original_sentence: str

class AnalysisData(BaseModel):
    file_id: str
    analysis_status: str
    document_subject: str
    document_purpose: str
    core_structure: List[CoreStructure]
    key_sentences: List[KeySentence]
    key_keywords: KeyKeywords
    verification_candidates: List[VerificationCandidate]
    evidence_grounding: List[EvidenceGrounding]
    recommended_departments: List[str] = []  # AI 추천 부서 목록 (기본값 빈 리스트)
    error_message: Optional[str] = None

class AnalyzeResponse(BaseModel):
    success: bool = True
    data: AnalysisData

# 4. Summarize Schemas
class MainContentItem(BaseModel):
    category: str
    points: List[str]

class SummaryResult(BaseModel):
    document_overview: List[str] = Field(..., description="문서 개요")
    document_purpose: str = Field(..., description="문서 목적")
    main_contents_list: List[MainContentItem] = Field(..., description="주요 내용 목록")
    conclusion_or_core_message: str = Field(..., description="결론 또는 핵심 메시지")
    error_message: Optional[str] = None

class SummaryData(BaseModel):
    file_id: str
    summary_result: SummaryResult

class SummarizeResponse(BaseModel):
    success: bool = True
    data: SummaryData

# 5. Validate Schemas
class ValidationIssueItem(BaseModel):
    issue_id: str = Field(..., description="문제 식별자")
    issue_type: str = Field(..., description="검증 항목 유형")
    issue_title: str = Field(..., description="문제 제목")
    reason_description: str = Field(..., description="문제가 되는 이유")
    relevant_original_evidence: str = Field(..., description="관련 원문 근거")

class HumanChecklistItem(BaseModel):
    check_id: str = Field(..., description="체크 항목 ID")
    title: str = Field(..., description="사람이 확인할 항목 제목")
    description: str = Field(..., description="상세 검토 지침")
    checked: bool = Field(False, description="확인 여부")

class ValidationResult(BaseModel):
    is_passed: bool = Field(..., description="검증 통과 여부")
    status_badge: str = Field(..., description="상태 뱃지 (정상, 확인 필요, 주의)")
    issue_list: List[ValidationIssueItem] = Field(..., description="확인이 필요한 문제 목록")
    human_review_checklist: List[HumanChecklistItem] = Field(..., description="사람이 확인할 항목")
    error_message: Optional[str] = None

class ValidationData(BaseModel):
    file_id: str
    validation_result: ValidationResult

class ValidateResponse(BaseModel):
    success: bool = True
    data: ValidationData

# 6. Archiving & Save Request Schemas
class ArchivingInfo(BaseModel):
    recommended_folder: str = Field(..., description="추천 분류 폴더 경로")
    recommended_filename: str = Field(..., description="추천 재지정 파일명")
    saved_folder: Optional[str] = Field(None, description="저장 폴더 경로")
    recommended_department: Optional[str] = Field(None, description="추천 소속 부서")
    department: Optional[str] = Field(None, description="소속 부서")

class DocumentInfo(BaseModel):
    original_filename: str
    format: str
    size_formatted: str
    uploaded_at: str

class IntegratedResultData(BaseModel):
    file_id: str
    status: str
    department: str = ""
    document_info: DocumentInfo
    archiving_info: ArchivingInfo
    analysis_data: AnalysisData
    summary_data: SummaryResult
    verification_data: ValidationResult

class IntegratedResultResponse(BaseModel):
    success: bool = True
    data: IntegratedResultData

class SaveDocumentRequest(BaseModel):
    folder_path: str = Field(..., description="수정된 저장 대상 폴더 경로")
    filename: str = Field(..., description="수정된 파일명")
    document_overview: List[str] = Field(..., description="수정된 문서 개요 목록")
    department: Optional[str] = Field(None, description="수정된 소속 부서명")
    analysis_data: Optional[AnalysisData] = None
    summary_data: Optional[SummaryResult] = None
    verification_data: Optional[ValidationResult] = None

class SaveDocumentResponse(BaseModel):
    success: bool = True
    message: str
    file_id: str
    archived_file_path: str

# 7. Search & Update Schemas
class DepartmentListResponse(BaseModel):
    success: bool = True
    total_count: int
    data: List[str]

class SearchItem(BaseModel):
    file_id: str
    original_filename: str
    renamed_filename: str
    format: str
    department: str
    uploaded_at: str
    one_line_summary: str
    confidence_score: float
    status_badge: str

class SearchResponse(BaseModel):
    success: bool = True
    total_count: int
    data: List[SearchItem]

class SummaryUpdateRequest(BaseModel):
    one_line_summary: Optional[str] = None
    overview_summary: Optional[List[str]] = None

class DocumentResultsUpdate(BaseModel):
    """사용자가 수정한 분석·요약·검증 결과 전체를 저장하는 요청."""
    department: Optional[str] = Field(None, description="수정된 소속 부서명")
    analysis_data: AnalysisData
    summary_data: SummaryResult
    verification_data: ValidationResult

# 8. File Move & Folder Recommend Schemas
class MoveFileRequest(BaseModel):
    new_folder_path: str = Field(..., description="이동할 폴더 경로 (없으면 자동 생성)")
    new_filename: Optional[str] = Field(None, description="변경할 파일명. 생략 시 기존 파일명 유지")

class MoveFileResponse(BaseModel):
    success: bool = True
    message: str
    file_id: str
    old_path: str
    new_path: str

class FolderRecommendItem(BaseModel):
    folder_path: str = Field(..., description="추천 폴더 경로")
    score: float = Field(..., description="요약 내용 기반 적합도 점수 (0~1)")
    exists: bool = Field(..., description="실존 폴더 여부")

class FolderRecommendResponse(BaseModel):
    success: bool = True
    file_id: str
    recommendations: List[FolderRecommendItem]

class FolderRecommendRequest(BaseModel):
    summary: List[str] = []
    purpose: str = ""
    message: str = ""
    keywords: Dict[str, List[str]] = {}
    folders: List[str] = []

class DepartmentRecommendRequest(BaseModel):
    summary: List[str] = []
    purpose: str = ""
    message: str = ""
    keywords: Dict[str, List[str]] = {}

class DepartmentRecommendResponse(BaseModel):
    success: bool = True
    file_id: str
    recommendations: List[str]

# 9. Multi-file Work List & Batch Operations Schemas
class UnconfirmedDocumentItem(BaseModel):
    file_id: str
    original_filename: str
    renamed_filename: str
    saved_folder: str
    department: str = "디지털혁신팀"
    one_line_summary: str
    user_confirmed: bool = False
    file_missing: bool = False
    uploaded_at: str

class UnconfirmedListResponse(BaseModel):
    success: bool = True
    total_count: int
    data: List[UnconfirmedDocumentItem]

class ConfirmDocumentRequest(BaseModel):
    folder_path: str = Field(..., description="저장 대상 폴더 경로")
    document_overview: List[str] = Field(..., description="요약 개요 목록")
    department: Optional[str] = Field(None, description="소속 부서명")

class BatchConfirmItem(BaseModel):
    file_id: str
    folder_path: str
    document_overview: List[str]
    department: Optional[str] = None

class BatchConfirmRequest(BaseModel):
    items: List[BatchConfirmItem]

class BatchDeleteRequest(BaseModel):
    file_ids: List[str]
