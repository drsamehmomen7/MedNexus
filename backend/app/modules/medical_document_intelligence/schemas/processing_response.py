from dataclasses import dataclass, field
from typing import Any

@dataclass
class ProcessingResponse:

    success: bool = True

    message: str = ""

    error: str | None = None

    data: Any = None

    context_entities: list[Any] = field(default_factory=list)

    warnings: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    processing_time: float | None = None

    engine_name: str = ""

    engine_version: str = ""

    module_name: str = ""