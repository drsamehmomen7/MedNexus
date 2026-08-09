from __future__ import annotations

from pathlib import Path

from backend.app.modules.medical_document_intelligence.contracts.document_content import (
    DocumentContent,
)
from backend.app.modules.medical_document_intelligence.extractors.base import (
    BaseDocumentExtractor,
)


class TxtDocumentExtractor(BaseDocumentExtractor):
    """
    Extract plain text documents (.txt).

    Responsibilities:
        - Read UTF text files.
        - Detect basic encoding.
        - Produce a unified DocumentContent contract.

    Responsibilities NOT included:
        - De-identification
        - NLP
        - Clinical understanding
        - Policy application
    """

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        return (".txt",)

    @property
    def media_type(self) -> str:
        return "text/plain"

    def extract(
        self,
        path: str | Path,
    ) -> DocumentContent:

        file_path = Path(path)

        if not file_path.exists():
            raise FileNotFoundError(file_path)

        if not file_path.is_file():
            raise ValueError(
                f"{file_path} is not a file."
            )

        encodings = (
            "utf-8",
            "utf-8-sig",
            "cp1252",
            "latin-1",
        )

        last_exception = None

        for encoding in encodings:

            try:

                text = file_path.read_text(
                    encoding=encoding,
                )

                return DocumentContent(
                    text=text,
                    source_name=file_path.name,
                    media_type=self.media_type,
                    extension=file_path.suffix,
                    file_size=file_path.stat().st_size,
                    encoding=encoding,
                    page_count=1,
                    metadata={
                        "extractor": "txt",
                    },
                )

            except UnicodeDecodeError as exc:
                last_exception = exc

        raise UnicodeDecodeError(
            last_exception.encoding,
            last_exception.object,
            last_exception.start,
            last_exception.end,
            "Unable to decode text file using supported encodings.",
        )