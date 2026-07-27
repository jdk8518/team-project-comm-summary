from app.core.security import mask_data


def mask_result_for_display(result: dict) -> dict:
    return mask_data(result)
