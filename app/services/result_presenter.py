from app.services.masking import mask_result_for_display


def present_result(result: dict) -> dict:
    return mask_result_for_display(result)
