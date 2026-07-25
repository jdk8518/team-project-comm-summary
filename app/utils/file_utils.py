"""
app/utils/file_utils.py
Rule-based File & Path Utilities Layer
"""
import os
import re
from typing import Tuple
from datetime import datetime


def clean_folder_segment(segment: str) -> str:
    cleaned = segment.strip().replace("\\", "/")
    cleaned = re.sub(r'[\:*?"<>|]', "", cleaned)
    cleaned = re.sub(r'/+', '/', cleaned)
    return cleaned.strip('/')


def clean_filename_stem(filename: str) -> str:
    stem, ext = os.path.splitext(filename)
    stem = re.sub(r'[\:*?"<>|/]', "", stem).strip()
    ext = ext.strip()
    return f"{stem}{ext}" if stem else filename


def compute_archiving_paths(original_filename: str, department: str = "디지털혁신팀") -> Tuple[str, str]:
    today_str = datetime.now().strftime("%Y%m%d")
    clean_dept = clean_folder_segment(department or "디지털혁신팀") or "디지털혁신팀"
    rec_folder = f"{clean_dept}/{today_str}"

    stem, ext = os.path.splitext(original_filename)
    if not ext:
        ext = ".pdf"
    clean_stem = re.sub(r'[\:*?"<>|/]', "", stem).strip() or "문서"
    rec_filename = f"{today_str}_{clean_dept}_{clean_stem}{ext}"
    return rec_folder, rec_filename
