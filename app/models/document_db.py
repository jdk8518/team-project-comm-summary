"""
app/models/document_db.py
Persistence and SQLite DB Layer

SQLite DB 연결, 테이블 초기화, CRUD 및 파일 아카이빙 영속성 관리.
현재 MVP 단계에서는 app.db의 함수를 re-export하며,
향후 ORM 도입 시 이 모듈에서 Model 클래스를 정의합니다.

입력:  file_id (str), 각종 CRUD 파라미터
출력:  dict (문서 레코드), bool (성공 여부), str (경로 또는 오류 메시지)
"""
from app.db import (
    get_db_connection,
    init_sqlite_db,
    get_database_status,
    store_uploaded_document,
    update_document_extracted,
    update_document_analysis,
    update_document_summary,
    update_document_validation,
    update_document_recommendation,
    update_document_results,
    update_summary_content,
    get_document_by_id,
    get_document_file_bytes,
    get_all_departments,
    get_unconfirmed_documents,
    get_existing_archive_folders,
    get_folder_tree,
    search_documents_in_db,
    archive_and_save_document,
    save_doc_to_sqlite,
    confirm_document,
    batch_confirm_documents,
    batch_delete_documents,
    delete_document_from_db,
    move_document_file,
    document_db,
    document_files,
    ARCHIVE_ROOT,
    DB_PATH,
)

__all__ = [
    "get_db_connection",
    "init_sqlite_db",
    "get_database_status",
    "store_uploaded_document",
    "update_document_extracted",
    "update_document_analysis",
    "update_document_summary",
    "update_document_validation",
    "update_document_recommendation",
    "update_document_results",
    "update_summary_content",
    "get_document_by_id",
    "get_document_file_bytes",
    "get_all_departments",
    "get_unconfirmed_documents",
    "get_existing_archive_folders",
    "get_folder_tree",
    "search_documents_in_db",
    "archive_and_save_document",
    "save_doc_to_sqlite",
    "confirm_document",
    "batch_confirm_documents",
    "batch_delete_documents",
    "delete_document_from_db",
    "move_document_file",
    "document_db",
    "document_files",
    "ARCHIVE_ROOT",
    "DB_PATH",
]
