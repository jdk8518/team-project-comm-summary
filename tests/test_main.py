from app.utils.file_utils import clean_text


def test_clean_text_normalizes_whitespace() -> None:
    assert clean_text("회의   결과\n\n\n다음 일정") == "회의 결과\n\n다음 일정"
