import os
import uuid
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
import io

from app.schemas import (
    IntegratedResultResponse, IntegratedResultData, DocumentInfo, ArchivingInfo,
    AnalysisData, SummaryResult, ValidationResult,
    SaveDocumentRequest, SaveDocumentResponse,
    SearchResponse, SearchItem, SummaryUpdateRequest,
    MoveFileRequest, MoveFileResponse,
    FolderRecommendItem, FolderRecommendResponse,
)
from app.parsers import validate_file_metadata, extract_text_from_file, structure_text, DocumentParsingError
from app.services import run_document_analysis, run_document_summarization, run_document_validation, recommend_folder
from app import db

router = APIRouter(prefix="/api/v1/documents", tags=["Document AI Analysis System"])

@router.post("/analyze", response_model=IntegratedResultResponse, summary="문서 분석 통합 API (대시보드 UI 연동)")
async def analyze_document(file: UploadFile = File(...)):
    """
    단일 문서(PDF, DOCX, TXT, HWP, HWPX, PPTX)를 수신하여
    텍스트 파싱 -> AI 구조 분석 -> AI 팩트 요약 -> AI 검증
    결과와 추천 폴더/파일명 아카이빙 정보를 통합 반환합니다.
    """
    file_bytes = await file.read()
    file_size = len(file_bytes)
    filename = file.filename or "unknown.pdf"

    # 1. 3단계 유효성 검증
    format_str = validate_file_metadata(filename, file_size)

    # 2. 파일 보관 및 DB 저장
    file_id = f"doc_{uuid.uuid4()}"
    temp_dir = "temp/uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{file_id}_{filename}")
    
    with open(temp_path, "wb") as f:
        f.write(file_bytes)

    db.store_uploaded_document(
        file_id=file_id,
        original_filename=filename,
        format_str=format_str,
        file_bytes=file_bytes,
        file_path=temp_path
    )

    # 3. 텍스트 파싱
    raw_cleaned_text = extract_text_from_file(file_bytes, format_str)
    structured_content_dict = structure_text(raw_cleaned_text)
    db.update_document_extracted(file_id, raw_cleaned_text, structured_content_dict)

    # 4. AI 문서 핵심 구조 분석
    analysis_data = run_document_analysis(file_id, raw_cleaned_text, structured_content_dict)
    db.update_document_analysis(file_id, analysis_data)

    # 5. AI 요약 생성
    summary_data = run_document_summarization(file_id, raw_cleaned_text, analysis_data)
    db.update_document_summary(file_id, summary_data)

    # 6. AI 검증 수행
    validation_data = run_document_validation(
        file_id=file_id,
        raw_text=raw_cleaned_text,
        analysis_data=analysis_data,
        summary_data=summary_data
    )
    db.update_document_validation(file_id, validation_data)

    # 7. UI 바인딩용 통합 결과 구성
    size_formatted = f"{file_size / (1024*1024):.1f} MB" if file_size >= 1024*1024 else f"{file_size / 1024:.1f} KB"
    doc_record = db.get_document_by_id(file_id)

    integrated_data = IntegratedResultData(
        file_id=file_id,
        status="COMPLETED",
        document_info=DocumentInfo(
            original_filename=filename,
            format=format_str,
            size_formatted=size_formatted,
            uploaded_at=doc_record["uploaded_at"]
        ),
        archiving_info=ArchivingInfo(
            recommended_folder=doc_record["recommended_folder"],
            recommended_filename=doc_record["recommended_filename"]
        ),
        analysis_data=analysis_data,
        summary_data=summary_data.summary_result,
        verification_data=validation_data.validation_result
    )

    return IntegratedResultResponse(success=True, data=integrated_data)

@router.post("/{file_id}/save", response_model=SaveDocumentResponse, summary="지정한 폴더/파일명 원본 저장 및 DB 요약 저장 API")
async def save_document(file_id: str, req: SaveDocumentRequest):
    """
    지정한 폴더 경로와 파일명으로 원본 문서 파일을 실재 보관하고,
    수정된 요약 내용을 DB에 추가/업데이트 저장합니다.
    """
    success, res_path = db.archive_and_save_document(
        file_id=file_id,
        folder_path=req.folder_path,
        filename=req.filename,
        document_overview=req.document_overview
    )

    if not success:
        raise HTTPException(status_code=400, detail=res_path)

    return SaveDocumentResponse(
        success=True,
        message="원문 파일 보관 및 요약 내역이 DB에 성공적으로 저장되었습니다.",
        file_id=file_id,
        archived_file_path=res_path
    )

@router.get("/search", response_model=SearchResponse, summary="DB 요약 다각도 검색 API")
async def search_documents(
    keyword: Optional[str] = Query(None, description="검색어 (키워드, 요약문, 제목)"),
    department: Optional[str] = Query(None, description="소속 부서명"),
    folder: Optional[str] = Query(None, description="폴더 경로 필터 (해당 폴더 저장 문서만 반환)"),
):
    results = db.search_documents_in_db(keyword, department)

    # 폴더 필터: 지정한 경우 saved_folder 또는 recommended_folder가 일치하는 문서만 반환
    if folder and folder.strip():
        try:
            normalized = db.normalize_archive_folder_path(folder).rstrip("/")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if not db.is_archive_root(normalized):
            filtered = []
            for item in results:
                doc = db.get_document_by_id(item["file_id"])
                if doc:
                    doc_folder = db.normalize_archive_folder_path(
                        doc.get("saved_folder") or doc.get("recommended_folder", "")
                    ).rstrip("/")
                    if doc_folder == normalized or doc_folder.startswith(f"{normalized}/"):
                        filtered.append(item)
            results = filtered

    items = [SearchItem(**r) for r in results]
    return SearchResponse(success=True, total_count=len(items), data=items)

@router.get("/folder-tree", summary="폴더 계층 구조 조회 API")
async def get_folder_tree():
    """
    DB에 저장된 전체 문서를 폴더 경로 기준으로 계층화하여 반환합니다.
    파일 검색 화면의 좌측 폴더 탐색기 패널에 사용합니다.
    """
    tree = db.get_folder_tree()
    return {"success": True, **tree}

@router.get("/{file_id}/result", response_model=IntegratedResultResponse, summary="특정 문서의 통합 결과 조회 API")
async def get_document_result(file_id: str):
    doc = db.get_document_by_id(file_id)
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

    size_formatted = f"{doc['size_bytes'] / (1024*1024):.1f} MB" if doc['size_bytes'] >= 1024*1024 else f"{doc['size_bytes'] / 1024:.1f} KB"
    analysis = doc.get("analysis_data") or run_document_analysis(file_id, doc.get("raw_text", ""), doc.get("structured_content", {}))
    summary_data_obj = doc.get("summary_data") or run_document_summarization(file_id, doc.get("raw_text", ""), analysis)
    validation = doc.get("validation_data") or run_document_validation(file_id, doc.get("raw_text", ""), analysis, summary_data_obj)

    integrated_data = IntegratedResultData(
        file_id=file_id,
        status=doc.get("status", "COMPLETED"),
        document_info=DocumentInfo(
            original_filename=doc["original_filename"],
            format=doc["format"],
            size_formatted=size_formatted,
            uploaded_at=doc["uploaded_at"]
        ),
        archiving_info=ArchivingInfo(
            recommended_folder=doc.get("saved_folder", doc.get("recommended_folder", "output/archive/디지털혁신팀/")),
            recommended_filename=doc.get("saved_filename", doc.get("recommended_filename", doc["original_filename"]))
        ),
        analysis_data=analysis,
        summary_data=summary_data_obj.summary_result,
        verification_data=validation.validation_result
    )

    return IntegratedResultResponse(success=True, data=integrated_data)

@router.put("/{file_id}/summary", summary="요약 내용 수정 API")
async def update_summary(file_id: str, req: SummaryUpdateRequest):
    success = db.update_summary_content(file_id, req.one_line_summary, req.overview_summary)
    if not success:
        raise HTTPException(status_code=404, detail="요약 내용을 업데이트할 수 없습니다.")
    return {"success": True, "message": "요약 내용이 DB에 성공적으로 수정되었습니다."}

@router.get("/{file_id}/download", summary="원본 파일 1-Click 다운로드 API")
async def download_original_file(file_id: str):
    file_data = db.get_document_file_bytes(file_id)
    if not file_data:
        raise HTTPException(status_code=404, detail="원본 파일이 존재하지 않습니다.")

    file_bytes, filename = file_data
    stream = io.BytesIO(file_bytes)
    
    from urllib.parse import quote
    encoded_filename = quote(filename)
    headers = {
        "Content-Disposition": f"attachment; filename=\"{encoded_filename}\"; filename*=UTF-8''{encoded_filename}"
    }
    return StreamingResponse(stream, media_type="application/octet-stream", headers=headers)

@router.delete("/{file_id}", summary="DB 레코드 및 아카이빙 원본 파일 삭제 API")
async def delete_document(file_id: str):
    """
    DB 레코드를 삭제하고 아카이빙된 원본 파일을 파일시스템에서 제거합니다.
    삭제된 문서는 복구할 수 없습니다.
    """
    success, message = db.delete_document_from_db(file_id)
    if not success:
        raise HTTPException(status_code=404, detail=message)
    return {"success": True, "message": message, "file_id": file_id}

@router.put("/{file_id}/folder", response_model=MoveFileResponse, summary="아카이빙 파일 저장 경로 이동 API")
async def move_document_folder(file_id: str, req: MoveFileRequest):
    """
    지정한 새 폴더 경로로 원본 파일을 이동합니다.
    경로가 없으면 자동으로 폴더를 생성합니다.
    """
    doc = db.get_document_by_id(file_id)
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

    success, old_path, new_path = db.move_document_file(
        file_id=file_id,
        new_folder_path=req.new_folder_path,
        new_filename=req.new_filename,
    )
    if not success:
        # new_path에 오류 메시지가 담겨 있음
        raise HTTPException(status_code=400, detail=new_path)

    return MoveFileResponse(
        success=True,
        message="파일이 새 경로로 성공적으로 이동되었습니다.",
        file_id=file_id,
        old_path=old_path,
        new_path=new_path,
    )

@router.get("/{file_id}/recommend-folder", response_model=FolderRecommendResponse, summary="요약 기반 저장 경로 추천 API")
async def recommend_document_folder(file_id: str):
    """
    저장된 요약 키워드를 바탕으로 output/archive/ 하위 실존 폴더 중
    가장 근접한 경로를 상위 3개 추천합니다.
    """
    doc = db.get_document_by_id(file_id)
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

    # 추천 키워드: 조직명 + 개념어 + 부서명
    analysis = doc.get("analysis_data")
    keywords: list[str] = [doc.get("department", "")]
    if analysis and hasattr(analysis, "key_keywords"):
        kw = analysis.key_keywords
        keywords += kw.organizations + kw.concepts

    existing_folders = db.get_existing_archive_folders()
    recommendations = recommend_folder(existing_folders, keywords)

    return FolderRecommendResponse(
        success=True,
        file_id=file_id,
        recommendations=[FolderRecommendItem(**r) for r in recommendations],
    )

# Alias routes
@router.post("/api/documents/analyze", response_model=IntegratedResultResponse, include_in_schema=False)
async def analyze_document_alias(file: UploadFile = File(...)):
    return await analyze_document(file)

@router.post("/api/documents/save", response_model=SaveDocumentResponse, include_in_schema=False)
async def save_document_alias(file_id: str, req: SaveDocumentRequest):
    return await save_document(file_id, req)

@router.get("/api/documents/search", response_model=SearchResponse, include_in_schema=False)
async def search_documents_alias(
    keyword: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    folder: Optional[str] = Query(None),
):
    return await search_documents(keyword, department, folder)

@router.delete("/api/documents/{file_id}", include_in_schema=False)
async def delete_document_alias(file_id: str):
    return await delete_document(file_id)
