import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    max_file_size: int = 10 * 1024 * 1024
    max_text_length: int = 100_000_000
    max_llm_input_chars: int = int(os.getenv("MAX_LLM_INPUT_CHARS", "30000"))
    chunk_overlap_chars: int = int(os.getenv("CHUNK_OVERLAP_CHARS", "500"))
    max_analysis_chunks: int = int(os.getenv("MAX_ANALYSIS_CHUNKS", "4000"))
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    tesseract_cmd: str = os.getenv("TESSERACT_CMD", "").strip()
    tessdata_dir: str = os.getenv("TESSDATA_DIR", "").strip()
    default_categories: tuple[str, ...] = ("회의록", "공문", "보고서", "공고문")
    project_root: Path = Path(__file__).resolve().parents[2]

    @property
    def output_directories(self) -> dict[str, Path]:
        return {
            "회의록": self.project_root / "other_docs" / "meeting",
            "공문": self.project_root / "other_docs" / "official document",
            "보고서": self.project_root / "other_docs" / "report",
            "공고문": self.project_root / "other_docs" / "public notice",
            "기타(예외)": self.project_root / "other_docs" / "others",
        }



settings = Settings()
