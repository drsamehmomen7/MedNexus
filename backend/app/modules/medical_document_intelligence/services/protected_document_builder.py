from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from io import BytesIO
from pathlib import Path
from threading import RLock
from typing import Mapping

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


@dataclass(frozen=True, slots=True)
class GeneratedProtectedPdf:
    content: bytes
    filename: str
    media_type: str
    page_count: int
    generated_at: str
    integrity_sha256: str
    provenance: Mapping[str, str]


class ProtectedDocumentBuilder:
    """Build a new clinical PDF from authoritative protected text only."""

    MEDIA_TYPE = "application/pdf"
    BUILDER_VERSION = "1.0"
    _font_lock = RLock()
    _fonts_registered = False
    _body_font = "Helvetica"
    _bold_font = "Helvetica-Bold"

    def build_pdf(self, *, source_filename: str, protected_text: str) -> GeneratedProtectedPdf:
        if not isinstance(protected_text, str) or not protected_text.strip():
            raise ValueError("protected_text must contain readable document content.")

        body_font, bold_font = self._ensure_fonts()
        output = BytesIO()
        document = SimpleDocTemplate(
            output,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=25 * mm,
            bottomMargin=22 * mm,
            title="Protected Clinical Report",
            author="MRJ - Medical Report Journey",
            subject="Protected medical document",
            creator="MRJ Protected Document Builder",
            allowSplitting=1,
        )
        body_style = ParagraphStyle(
            "MRJProtectedBody",
            fontName=body_font,
            fontSize=10.5,
            leading=15.5,
            textColor=colors.HexColor("#1C140C"),
            spaceAfter=1.5 * mm,
            splitLongWords=True,
        )
        rtl_body_style = ParagraphStyle(
            "MRJProtectedBodyRTL",
            parent=body_style,
            alignment=TA_RIGHT,
            shaping=True,
        )
        heading_style = ParagraphStyle(
            "MRJProtectedHeading",
            parent=body_style,
            fontName=bold_font,
            fontSize=11.5,
            leading=15,
            textColor=colors.HexColor("#07575A"),
            spaceBefore=3.5 * mm,
            spaceAfter=1.5 * mm,
            keepWithNext=True,
        )
        rtl_heading_style = ParagraphStyle(
            "MRJProtectedHeadingRTL",
            parent=heading_style,
            alignment=TA_RIGHT,
            shaping=True,
        )

        story = []
        for raw_line in protected_text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            line = raw_line.rstrip()
            if not line.strip():
                story.append(Spacer(1, 3.5 * mm))
                continue
            rtl = self._is_rtl(line)
            heading = self._is_section_heading(line)
            style = (
                rtl_heading_style
                if rtl and heading
                else heading_style
                if heading
                else rtl_body_style
                if rtl
                else body_style
            )
            markup = (
                self._rtl_markup(
                    line,
                    font_name=bold_font if heading else body_font,
                    font_size=11.5 if heading else 10.5,
                    max_width=A4[0] - (36 * mm),
                )
                if rtl
                else escape(line).replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;")
            )
            story.append(Paragraph(markup, style))

        document.build(
            story,
            onFirstPage=self._decorate_page,
            onLaterPages=self._decorate_page,
        )
        content = output.getvalue()
        reader = PdfReader(BytesIO(content), strict=False)
        page_count = len(reader.pages)
        if not content.startswith(b"%PDF") or page_count < 1:
            raise RuntimeError("Protected PDF generation did not produce a valid document.")

        generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return GeneratedProtectedPdf(
            content=content,
            filename=self.protected_filename(source_filename),
            media_type=self.MEDIA_TYPE,
            page_count=page_count,
            generated_at=generated_at,
            integrity_sha256=hashlib.sha256(content).hexdigest(),
            provenance={
                "builder": "MRJProtectedDocumentBuilder",
                "builder_version": self.BUILDER_VERSION,
                "strategy": "deterministic_text_rebuild",
                "source_media_type": self.MEDIA_TYPE,
                "content_authority": "protected_text",
            },
        )

    @staticmethod
    def protected_filename(source_filename: str) -> str:
        stem = Path(str(source_filename or "medical_report")).stem
        safe_stem = re.sub(r"[\x00-\x1f<>:\"/\\|?*]+", "_", stem)
        safe_stem = re.sub(r"\s+", " ", safe_stem).strip(" ._") or "medical_report"
        if safe_stem.upper().endswith("_PROTECTED"):
            safe_stem = safe_stem[: -len("_PROTECTED")].rstrip(" ._")
        return f"{safe_stem[:120]}_PROTECTED.pdf"

    @classmethod
    def _ensure_fonts(cls) -> tuple[str, str]:
        with cls._font_lock:
            if cls._fonts_registered:
                return cls._body_font, cls._bold_font

            for regular, bold in cls._font_candidates():
                if regular.is_file():
                    pdfmetrics.registerFont(TTFont("MRJClinical", str(regular)))
                    selected_bold = bold if bold and bold.is_file() else regular
                    pdfmetrics.registerFont(TTFont("MRJClinicalBold", str(selected_bold)))
                    cls._body_font = "MRJClinical"
                    cls._bold_font = "MRJClinicalBold"
                    cls._fonts_registered = True
                    return cls._body_font, cls._bold_font

            raise RuntimeError(
                "A Unicode clinical document font is required to build protected PDFs."
            )

    @staticmethod
    def _font_candidates() -> tuple[tuple[Path, Path | None], ...]:
        windows_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        return (
            (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),
            (Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"), Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf")),
            (windows_fonts / "ARIALUNI.TTF", windows_fonts / "arialbd.ttf"),
            (windows_fonts / "segoeui.ttf", windows_fonts / "segoeuib.ttf"),
            (windows_fonts / "arial.ttf", windows_fonts / "arialbd.ttf"),
            (Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"), None),
        )

    @staticmethod
    def _is_rtl(value: str) -> bool:
        rtl = sum("\u0590" <= character <= "\u08ff" for character in value)
        letters = sum(character.isalpha() for character in value)
        return rtl > 0 and rtl >= max(1, letters // 2)

    @staticmethod
    def _is_section_heading(value: str) -> bool:
        text = value.strip()
        if len(text) > 80:
            return False
        if text.endswith(":") and len(text.split()) <= 8:
            return True
        latin_letters = [character for character in text if character.isalpha()]
        return bool(latin_letters) and all(character.isupper() for character in latin_letters)

    @staticmethod
    def _rtl_markup(
        value: str,
        *,
        font_name: str,
        font_size: float,
        max_width: float,
    ) -> str:
        """Return visually ordered, pre-wrapped RTL markup for ReportLab.

        ReportLab's optional rlbidi package has no supported Windows wheel in the
        retained runtime. HarfBuzz still shapes each logical word correctly, so
        MRJ performs only the missing deterministic word-order and line-wrap step.
        The authoritative protected text is never altered.
        """

        words = value.expandtabs(4).split()
        if not words:
            return ""

        logical_lines: list[list[str]] = []
        current: list[str] = []
        current_width = 0.0
        space_width = pdfmetrics.stringWidth(" ", font_name, font_size)
        for word in words:
            word_width = pdfmetrics.stringWidth(word, font_name, font_size)
            candidate_width = current_width + (space_width if current else 0.0) + word_width
            if current and candidate_width > max_width:
                logical_lines.append(current)
                current = [word]
                current_width = word_width
            else:
                current.append(word)
                current_width = candidate_width
        if current:
            logical_lines.append(current)

        return "<br/>".join(
            " ".join(escape(word) for word in reversed(logical_line))
            for logical_line in logical_lines
        )

    @classmethod
    def _decorate_page(cls, canvas, document) -> None:
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(colors.HexColor("#D4BC96"))
        canvas.setLineWidth(0.5)
        canvas.line(18 * mm, height - 17 * mm, width - 18 * mm, height - 17 * mm)
        canvas.setFont(cls._body_font, 8.5)
        canvas.setFillColor(colors.HexColor("#07575A"))
        canvas.drawString(18 * mm, height - 13 * mm, "PROTECTED CLINICAL REPORT")
        canvas.setFont(cls._body_font, 8)
        canvas.setFillColor(colors.HexColor("#6E5C48"))
        canvas.drawRightString(width - 18 * mm, height - 13 * mm, f"Page {document.page}")
        canvas.line(18 * mm, 15 * mm, width - 18 * mm, 15 * mm)
        canvas.drawCentredString(
            width / 2,
            10.5 * mm,
            "Protected by MRJ | Medical Report Journey",
        )
        canvas.restoreState()


protected_document_builder = ProtectedDocumentBuilder()
