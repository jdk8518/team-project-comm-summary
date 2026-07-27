from app.core.security import mask_text
from app.services.document_analysis import analyze_document
from app.services.summarization import create_summary


def analyze_extracted_document(document_id: str, document: dict, text: str, categories: list[str]) -> dict:
    """Analyze extracted text and create a grounded summary without verification."""
    analysis = analyze_document(mask_text(text), categories)
    summary = create_summary(text, analysis)
    enriched_document = {
        **document,
        "title": analysis["title"],
        "organization": analysis["organization"],
        "department": analysis["department"],
    }
    return {
        "document_id": document_id,
        "status": "SUMMARIZED",
        "document": enriched_document,
        "analysis": analysis,
        "summary": summary,
    }
