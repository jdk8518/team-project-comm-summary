from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any


@dataclass
class DocumentMetadata:
    document_id: str
    file_name: str
    extension: str
    file_size: int
    reference_date: date
    reference_date_source: str
    title: str = "확인 필요"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["reference_date"] = self.reference_date.isoformat()
        return data
