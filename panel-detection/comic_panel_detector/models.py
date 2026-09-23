from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class BoundingBox:
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass
class Panel:
    id: Optional[str]

    order: int

    bbox: BoundingBox

    width: int
    height: int

    area: int
    area_ratio: float

    confidence: Optional[float]

    class_id: Optional[int]

    class_name: Optional[str]

    source: str = "model"


@dataclass
class CoverageInfo:

    covered_ratio: float

    uncovered_ratio: float

    covered_area: int

    uncovered_area: int


@dataclass
class Page:

    page_number: int

    filename: str

    width: int

    height: int

    panels: List[Panel] = field(default_factory=list)

    coverage: Optional[CoverageInfo] = None

    error: Optional[str] = None