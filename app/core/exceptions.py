from fastapi import HTTPException


class DocumentProcessingError(HTTPException):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(status_code=status_code, detail=detail)


def bad_request(message: str) -> DocumentProcessingError:
    return DocumentProcessingError(400, message)


def unprocessable(message: str) -> DocumentProcessingError:
    return DocumentProcessingError(422, message)


def ai_unavailable(message: str) -> DocumentProcessingError:
    return DocumentProcessingError(503, message)


def ai_response_invalid(message: str) -> DocumentProcessingError:
    return DocumentProcessingError(502, message)
