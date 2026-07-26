"""
app/api/routes/documents.py
Presentation / Router Layer — 문서 분석 API 엔드포인트 정의

계층적 모놀리스 구조:
  Router → Service → Agent → Model
"""
import os
import uuid
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Form
from fastapi.responses import PlainTextResponse, StreamingResponse, JSONResponse
import io

from app.schemas import (
    IntegratedResultResponse, IntegratedResultData, DocumentInfo, ArchivingInfo,
    AnalysisData, SummaryResult, ValidationResult,
    SaveDocumentRequest, SaveDocumentResponse,
    DocumentResultsUpdate,
    FolderRecommendRequest,
    SearchResponse, SearchItem, SummaryUpdateRequest,
    MoveFileRequest, MoveFileResponse,
    FolderRecommendItem, FolderRecommendResponse,
    UnconfirmedDocumentItem, UnconfirmedListResponse,
    ConfirmDocumentRequest, BatchConfirmItem, BatchConfirmRequest, BatchDeleteRequest,
    DepartmentListResponse, DepartmentRecommendRequest, DepartmentRecommendResponse,
)
from app.parsers import validate_file_metadata, extract_text_from_file, structure_text, DocumentParsingError
from app.services import run_document_analysis, run_document_summarization, run_document_validation, recommend_folder, recommend_department
from app import db

router = APIRouter(prefix="/api/v1/documents", tags=["Document AI Analysis System"])


@router.get("/health/db", summary="MVP DB 연결 상태 조회 API")
async def database_health():
    """Expose the current backend status and its persistence limitation."""
    status = db.get_database_status()
    return {"success": status.get("connected", False), "data": status}

@router.post("/analyze", response_model=IntegratedResultResponse, summary="문서 분석 통합 API (대시보드 UI 연동)")
async def analyze_document(
    file: UploadFile = File(...),
    department: Optional[str] = Form(None),
    target_folder: Optional[str] = Form(None)
):
    """
    단일 문서(PDF, DOCX, TXT, HWP, HWPX, PPTX)를 수신하여
    텍스트 파싱 -> AI 구조 분석 -> AI 팩트 요약 -> AI 검증
    결과와 추천 폴더/파일명 아카이빙 정보를 통합 반환합니다.
    - department가 공백이거나 '부서 추천'인 경우 AI가 부서를 추천하여 지정합니다.
    """
    file_bytes = await file.read()
    file_size = len(file_bytes)
    raw_filename = file.filename or "unknown.pdf"
    filename = os.path.basename(raw_filename.replace("\\", "/")) or "unknown.pdf"

    raw_dept = (department or "").strip()
    use_ai_dept = not raw_dept or raw_dept == "부서 추천"

    # 1. 3단계 유효성 검증
    format_str = validate_file_metadata(filename, file_size)

    # 2. 파일 보관 및 DB 저장
    file_id = f"doc_{uuid.uuid4()}"
    temp_dir = "temp/uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{file_id}_{filename}")

    with open(temp_path, "wb") as f:
        f.write(file_bytes)

    # 3. 텍스트 파싱
    raw_cleaned_text = extract_text_from_file(file_bytes, format_str)
    structured_content_dict = structure_text(raw_cleaned_text)

    # 4. AI 문서 핵심 구조 분석 (기존 부서 목록 제공 → 추천 부서 3개 산출)
    existing_departments = db.get_all_departments()
    analysis_data = run_document_analysis(
        file_id, raw_cleaned_text, structured_content_dict,
        existing_departments=existing_departments
    )

    # 부서 결정
    if use_ai_dept:
        rec_depts = getattr(analysis_data, "recommended_departments", [])
        final_dept = rec_depts[0] if (rec_depts and isinstance(rec_depts, list)) else "디지털혁신팀"
    else:
        final_dept = raw_dept

    db.store_uploaded_document(
        file_id=file_id,
        original_filename=filename,
        format_str=format_str,
        file_bytes=file_bytes,
        file_path=temp_path,
        department=final_dept
    )

    db.update_document_extracted(file_id, raw_cleaned_text, structured_content_dict)
    db.update_document_analysis(file_id, analysis_data)

    # AI 폴더 추천은 현재 파일 저장 루트에 실제로 존재하는 폴더만 후보로 사용한다.
    folder_candidates = db.get_existing_archive_folders()
    recommendation = recommend_folder(
        folder_candidates,
        [
            doc_record_keyword
            for doc_record_keyword in (
                analysis_data.document_purpose,
                *analysis_data.key_keywords.organizations,
                *analysis_data.key_keywords.concepts,
            )
            if doc_record_keyword
        ],
    )
    if recommendation:
        db.update_document_recommendation(file_id, recommendation[0]["folder_path"])

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

    pipeline_has_ai_error = any(
        getattr(result, "error_message", None)
        for result in (analysis_data, summary_data.summary_result, validation_data.validation_result)
    )
    integrated_data = IntegratedResultData(
        file_id=file_id,
        status="ERROR" if pipeline_has_ai_error else "COMPLETED",
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
        department=final_dept,
        analysis_data=analysis_data,
        summary_data=summary_data.summary_result,
        verification_data=validation_data.validation_result
    )

    return IntegratedResultResponse(success=True, data=integrated_data)

@router.get("/departments", response_model=DepartmentListResponse, summary="등록된 모든 소속 부서 목록 조회 API (오름차순)")
async def get_departments():
    depts = db.get_all_departments()
    return DepartmentListResponse(success=True, total_count=len(depts), data=depts)

@router.post("/analyze-auto", response_model=IntegratedResultResponse, summary="다중 파일 자동 분석 및 보관 API (user_confirmed = False)")
async def analyze_document_auto(
    file: UploadFile = File(...),
    department: Optional[str] = Form(None),
    target_folder: Optional[str] = Form(None)
):
    """
    다중 파일 업로드 시 개별 문서를 수신하여
    분석/요약/검증을 완료한 후 사용자 개입 없이 바로 DB와 원본/Markdown 파일로 보관(user_confirmed=False)합니다.
    - department가 공백이거나 '부서 추천'인 경우 AI가 부서를 추천
    - target_folder가 공백이거나 '경로 추천'인 경우 AI가 경로를 추천
    """
    raw_dept = (department or "").strip()
    use_ai_dept = not raw_dept or raw_dept == "부서 추천"

    raw_folder = (target_folder or "").strip()
    use_ai_folder = not raw_folder or raw_folder == "경로 추천"

    res = await analyze_document(file, department=None if use_ai_dept else raw_dept)
    file_id = res.data.file_id
    doc_record = db.get_document_by_id(file_id)

    final_dept = doc_record.get("department") if (use_ai_dept and doc_record) else (raw_dept or "디지털혁신팀")
    if not final_dept or final_dept == "부서 추천":
        final_dept = "디지털혁신팀"

    if use_ai_folder:
        rec_folder = (doc_record.get("recommended_folder") if doc_record else None) or f"output/archive/{final_dept}/"
    else:
        rec_folder = raw_folder

    rec_filename = (doc_record.get("recommended_filename") if doc_record else None) or (doc_record.get("original_filename") if doc_record else "doc.pdf")
    overview = getattr(res.data.summary_data, "document_overview", ["자동 분석 요약"])

    db.archive_and_save_document(
        file_id=file_id,
        folder_path=rec_folder,
        filename=rec_filename,
        document_overview=overview,
        department=final_dept,
    )
    if doc_record:
        doc_record["user_confirmed"] = False
        doc_record["department"] = final_dept
        doc_record["saved_folder"] = rec_folder
        db.save_doc_to_sqlite(doc_record)

    if res.data.archiving_info:
        res.data.archiving_info.recommended_folder = rec_folder
        res.data.archiving_info.saved_folder = rec_folder
        res.data.archiving_info.department = final_dept
    return res

@router.get("/unconfirmed", response_model=UnconfirmedListResponse, summary="미확인 다중파일 작업 리스트 조회 API")
async def get_unconfirmed_documents():
    results = db.get_unconfirmed_documents()
    items = [UnconfirmedDocumentItem(**r) for r in results]
    return UnconfirmedListResponse(success=True, total_count=len(items), data=items)

@router.put("/{file_id}/confirm", summary="단일 문서 확정 저장 API")
async def confirm_single_document(file_id: str, req: ConfirmDocumentRequest):
    success, msg = db.confirm_document(file_id, req.folder_path, req.document_overview, department=req.department)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg, "file_id": file_id}

@router.post("/batch-confirm", summary="다중 파일 일괄 확정 저장 API")
async def batch_confirm_documents(req: BatchConfirmRequest):
    items_list = [item.model_dump() for item in req.items]
    success_count, failed_ids = db.batch_confirm_documents(items_list)
    return {
        "success": True,
        "message": f"{success_count}개 문서가 성공적으로 확정 저장되었습니다.",
        "success_count": success_count,
        "failed_ids": failed_ids
    }

@router.post("/batch-delete", summary="다중 파일 일괄 삭제 API")
async def batch_delete_documents(req: BatchDeleteRequest):
    success_count, failed_ids = db.batch_delete_documents(req.file_ids)
    return {
        "success": True,
        "message": f"{success_count}개 문서가 성공적으로 삭제되었습니다.",
        "success_count": success_count,
        "failed_ids": failed_ids
    }

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
        document_overview=req.document_overview,
        analysis_data=req.analysis_data,
        summary_data=req.summary_data,
        verification_data=req.verification_data,
        department=req.department,
        user_confirmed=True,
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
    fields: Optional[List[str]] = Query(None, description="검색 대상 체크 항목 목록"),
):
    checked_fields_list: Optional[List[str]] = None
    if fields:
        parsed_fields = []
        for f in fields:
            parsed_fields.extend([item.strip() for item in f.split(",") if item.strip()])
        checked_fields_list = parsed_fields

    results = db.search_documents_in_db(
        keyword=keyword,
        department=department,
        folder=folder,
        checked_fields=checked_fields_list
    )

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

    try:
        size_bytes = doc.get("size_bytes") or 0
        if size_bytes >= 1024 * 1024:
            size_formatted = f"{size_bytes / (1024*1024):.1f} MB"
        else:
            size_formatted = f"{size_bytes / 1024:.1f} KB"

        analysis = doc.get("analysis_data") or run_document_analysis(file_id, doc.get("raw_text", ""), doc.get("structured_content", {}))
        summary_data_obj = doc.get("summary_data") or run_document_summarization(file_id, doc.get("raw_text", ""), analysis)
        validation = doc.get("validation_data") or run_document_validation(file_id, doc.get("raw_text", ""), analysis, summary_data_obj)

        summary_res = getattr(summary_data_obj, "summary_result", summary_data_obj) if summary_data_obj else None
        if isinstance(summary_res, dict):
            try:
                summary_res = SummaryResult(**summary_res)
            except Exception:
                pass

        val_res = getattr(validation, "validation_result", validation) if validation else None
        if isinstance(val_res, dict):
            try:
                val_res = ValidationResult(**val_res)
            except Exception:
                pass

        integrated_data = IntegratedResultData(
            file_id=file_id,
            status=doc.get("status", "COMPLETED"),
            document_info=DocumentInfo(
                original_filename=doc.get("original_filename") or "document.pdf",
                format=doc.get("format") or "PDF",
                size_formatted=size_formatted,
                uploaded_at=doc.get("uploaded_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ),
            archiving_info=ArchivingInfo(
                recommended_folder=doc.get("saved_folder") or doc.get("recommended_folder") or "output/archive/디지털혁신팀/",
                recommended_filename=doc.get("saved_filename") or doc.get("recommended_filename") or doc.get("original_filename") or "document"
            ),
            department=doc.get("department") or "",
            analysis_data=analysis,
            summary_data=summary_res,
            verification_data=val_res
        )

        return IntegratedResultResponse(success=True, data=integrated_data)
    except Exception as e:
        print(f"Error in get_document_result for {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"문서 상세 결과 생성 중 오류가 발생했습니다: {str(e)}")

@router.put("/{file_id}/summary", summary="요약 내용 수정 API")
async def update_summary(file_id: str, req: SummaryUpdateRequest):
    success = db.update_summary_content(file_id, req.one_line_summary, req.overview_summary)
    if not success:
        raise HTTPException(status_code=404, detail="요약 내용을 업데이트할 수 없습니다.")
    return {"success": True, "message": "요약 내용이 DB에 성공적으로 수정되었습니다."}

@router.put("/{file_id}/results", summary="AI 분석·요약·검증 결과 전체 수정 API")
async def update_document_results(file_id: str, req: DocumentResultsUpdate):
    success = db.update_document_results(
        file_id,
        req.analysis_data,
        req.summary_data,
        req.verification_data,
        department=req.department,
    )
    if not success:
        raise HTTPException(status_code=404, detail="문서 분석 결과를 업데이트할 수 없습니다.")
    return {"success": True, "message": "AI 분석·요약·검증 결과가 DB와 Markdown에 저장되었습니다."}

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


@router.get("/{file_id}/markdown", summary="저장된 AI 요약 Markdown 조회 API")
async def view_summary_markdown(file_id: str):
    doc = db.get_document_by_id(file_id)
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    markdown_path = doc.get("summary_path")
    if not markdown_path or not os.path.exists(markdown_path):
        raise HTTPException(status_code=404, detail="저장된 요약 Markdown 파일이 없습니다.")
    try:
        with open(markdown_path, "r", encoding="utf-8") as markdown_file:
            content = markdown_file.read()
    except OSError as exc:
        raise HTTPException(status_code=500, detail="요약 Markdown 파일을 읽을 수 없습니다.") from exc
    return PlainTextResponse(content, media_type="text/markdown", headers={"Content-Disposition": "inline"})

@router.delete("/{file_id}", summary="DB 레코드 및 아카이빙 원본 파일 삭제 API")
async def delete_document(
    file_id: str,
    force_db_only: bool = Query(False, description="원본 파일 미존재 시 DB 데이터만 삭제 진행 여부")
):
    """
    DB 레코드를 삭제하고 아카이빙된 원본 파일을 파일시스템에서 제거합니다.
    원본 파일이 없을 경우 force_db_only=true로 DB 데이터만 삭제할 수 있습니다.
    """
    success, status_code, message = db.delete_document_from_db(file_id, force_db_only=force_db_only)
    if not success:
        if status_code == "FILE_MISSING":
            return JSONResponse(
                status_code=409,
                content={
                    "success": False,
                    "file_missing": True,
                    "file_id": file_id,
                    "message": message,
                    "detail": message,
                }
            )
        raise HTTPException(status_code=404 if status_code == "NOT_FOUND" else 400, detail=message)
    return {"success": True, "message": message, "file_id": file_id, "file_missing": False}

@router.put("/{file_id}/folder", response_model=MoveFileResponse, summary="아카이빙 파일 저장 경로 이동 API")
async def move_document_folder(file_id: str, req: MoveFileRequest):
    """
    지정한 새 폴더 경로로 원본 파일을 이동합니다.
    경로가 없으면 자동으로 폴더를 생성합니다.
    """
    doc = db.get_document_by_id(file_id)
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

    requested_filename = req.new_filename or doc.get("saved_filename") or doc.get("original_filename")
    success, old_path, new_path = db.move_document_file(
        file_id=file_id,
        new_folder_path=req.new_folder_path,
        new_filename=req.new_filename,
    )
    if not success:
        raise HTTPException(status_code=400, detail=new_path)

    updated_doc = db.get_document_by_id(file_id)
    final_filename = updated_doc.get("saved_filename") if updated_doc else os.path.basename(new_path)

    if requested_filename and final_filename and requested_filename != final_filename:
        message = f"이동 위치에 동일한 이름의 파일이 존재하여 '{final_filename}'(으)로 저장되었습니다."
    else:
        message = "파일이 새 경로로 성공적으로 이동되었습니다."

    return MoveFileResponse(
        success=True,
        message=message,
        file_id=file_id,
        old_path=old_path,
        new_path=new_path,
    )

@router.get("/{file_id}/recommend-folder", response_model=FolderRecommendResponse, summary="요약 기반 저장 경로 추천 API")
@router.post("/{file_id}/recommend-folder", response_model=FolderRecommendResponse, summary="수정 결과 기반 저장 경로 추천 API")
async def recommend_document_folder_api(file_id: str, req: Optional[FolderRecommendRequest] = None):
    doc = db.get_document_by_id(file_id)
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

    folders = (req.folders if req and req.folders else None) or db.get_existing_archive_folders()

    if req:
        keywords = [*req.summary, req.purpose, req.message]
        for values in (req.keywords or {}).values():
            keywords.extend(values or [])
    else:
        sdata = doc.get("summary_data") or {}
        if hasattr(sdata, "document_overview"):
            overview = getattr(sdata, "document_overview", [])
            purpose = getattr(sdata, "document_purpose", "")
            message = getattr(sdata, "conclusion_or_core_message", "")
        elif isinstance(sdata, dict):
            overview = sdata.get("document_overview", [])
            purpose = sdata.get("document_purpose", "")
            message = sdata.get("conclusion_or_core_message", "")
        else:
            overview, purpose, message = [], "", ""
        keywords = [*overview, purpose, message, doc.get("department", "")]

    recommendations = recommend_folder(folders, keywords)
    return FolderRecommendResponse(
        success=True,
        file_id=file_id,
        recommendations=[FolderRecommendItem(**item) for item in recommendations[:3]],
    )


@router.get("/{file_id}/recommend-department", response_model=DepartmentRecommendResponse, summary="소속 부서 추천 API (GET)")
@router.post("/{file_id}/recommend-department", response_model=DepartmentRecommendResponse, summary="요약 기반 소속 부서 추천 API (POST)")
async def recommend_document_department_api(file_id: str, req: Optional[DepartmentRecommendRequest] = None):
    doc = db.get_document_by_id(file_id)
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

    all_depts = db.get_all_departments()

    if req:
        summary = req.summary
        purpose = req.purpose
        message = req.message
        keywords = req.keywords or {}
    else:
        sdata = doc.get("summary_data") or {}
        if hasattr(sdata, "document_overview"):
            summary = getattr(sdata, "document_overview", [])
            purpose = getattr(sdata, "document_purpose", "")
            message = getattr(sdata, "conclusion_or_core_message", "")
        elif isinstance(sdata, dict):
            summary = sdata.get("document_overview", [])
            purpose = sdata.get("document_purpose", "")
            message = sdata.get("conclusion_or_core_message", "")
        else:
            summary, purpose, message = [], "", ""

        adata = doc.get("analysis_data") or {}
        keywords = {}
        if hasattr(adata, "key_keywords") and adata.key_keywords:
            kw = adata.key_keywords
            keywords = {
                "persons": getattr(kw, "persons", []),
                "organizations": getattr(kw, "organizations", []),
                "schedules": getattr(kw, "schedules", []),
                "metrics": getattr(kw, "metrics", []),
                "concepts": getattr(kw, "concepts", []),
            }

    recommendations = recommend_department(all_depts, summary, purpose, message, keywords)
    return DepartmentRecommendResponse(success=True, file_id=file_id, recommendations=recommendations[:3])

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
    fields: Optional[List[str]] = Query(None),
):
    return await search_documents(keyword, department, folder, fields)

@router.delete("/api/documents/{file_id}", include_in_schema=False)
async def delete_document_alias(file_id: str):
    return await delete_document(file_id)
