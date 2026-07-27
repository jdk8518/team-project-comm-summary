from copy import deepcopy

from app.core.exceptions import bad_request

_sessions: dict[str, dict] = {}


def save_session(document_id: str, result: dict) -> None:
    _sessions[document_id] = deepcopy(result)


def get_session(document_id: str) -> dict:
    try:
        return deepcopy(_sessions[document_id])
    except KeyError as error:
        raise bad_request("분석 결과를 찾을 수 없습니다. 문서를 다시 분석해 주세요.") from error
