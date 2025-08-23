from __future__ import annotations

import io
import json
import mimetypes
import os
from email import policy
from email.parser import BytesParser
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.utils.logger import get_logger


def _safe_import(module: str, attr: Optional[str] = None):
    try:
        mod = __import__(module, fromlist=[attr] if attr else [])
        return getattr(mod, attr) if attr else mod
    except Exception:  # ImportError or others
        return None


chardet = _safe_import("chardet")
pdfminer_high_level = _safe_import("pdfminer.high_level")
docx_module = _safe_import("docx")
pptx_module = _safe_import("pptx")
bs4_module = _safe_import("bs4")
pandas_module = _safe_import("pandas")
ebooklib_module = _safe_import("ebooklib")
ebooklib_epub = _safe_import("ebooklib", "epub")
yaml_module = _safe_import("yaml")
PIL_Image = _safe_import("PIL.Image", None)
pytesseract_module = _safe_import("pytesseract")


class DocumentParserService:
    """Universal document parser service that extracts plain text from various file types.

    Supported categories (depending on optional deps availability):
    - Text/Markup: .txt, .md, .rst
    - PDF: .pdf (pdfminer.six)
    - Office: .docx (python-docx), .pptx (python-pptx), .xlsx (pandas/openpyxl), .csv
    - Open formats: .odt/.odp/.ods (best-effort via mimetype/text fallback if libs missing)
    - Web: .html/.htm (beautifulsoup4)
    - Data: .json/.ndjson, .yaml/.yml, .xml (xml via bs4 if lxml installed)
    - eBook: .epub (ebooklib)
    - Email: .eml (stdlib email)
    - Images: .png/.jpg/.jpeg/.tiff (OCR via pytesseract + Pillow if enabled)

    This service returns a list of "document chunks" where each item is a dict containing:
    {
        "content": str,           # extracted text
        "metadata": dict,         # additional context (e.g., page number, sheet name)
        "source": str,            # file name
        "mime_type": Optional[str]
    }
    """

    def __init__(self, ocr_enabled: Optional[bool] = None, ocr_lang: Optional[str] = None):
        self.logger = get_logger("document_parser_service")
        # Configure OCR from environment if not explicitly provided
        self.ocr_enabled = (
            bool(int(os.environ.get("PARSER_OCR_ENABLED", "0")))
            if ocr_enabled is None
            else bool(ocr_enabled)
        )
        self.ocr_lang = ocr_lang or os.environ.get("PARSER_OCR_LANG", "eng")

    # --------------------------- Public API ---------------------------
    def parse_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        with open(file_path, "rb") as f:
            data = f.read()
        file_name = os.path.basename(file_path)
        return self.parse_bytes(file_name=file_name, data=data, metadata=metadata)

    def parse_bytes(
        self,
        file_name: str,
        data: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        metadata = metadata or {}
        mime_type, _ = mimetypes.guess_type(file_name)
        ext = (os.path.splitext(file_name)[1] or "").lower()

        self.logger.info(f"Parsing file '{file_name}' (ext={ext}, mime={mime_type})")

        # Route based on extension first (fallback to mime/text)
        try:
            if ext in {".txt", ".md", ".rst", ".log"}:
                text = self._decode_text_bytes(data)
                return [self._build_chunk(text, file_name, mime_type, metadata)]

            if ext == ".pdf":
                return self._parse_pdf(data, file_name, mime_type, metadata)

            if ext == ".docx":
                return self._parse_docx(data, file_name, mime_type, metadata)

            if ext == ".pptx":
                return self._parse_pptx(data, file_name, mime_type, metadata)

            if ext in {".csv"}:
                return self._parse_csv(data, file_name, mime_type, metadata)

            if ext in {".xlsx"}:
                return self._parse_xlsx(data, file_name, mime_type, metadata)

            if ext in {".html", ".htm"}:
                return self._parse_html(data, file_name, mime_type, metadata)

            if ext in {".json", ".ndjson"}:
                return self._parse_json(data, file_name, mime_type, metadata)

            if ext in {".yaml", ".yml"}:
                return self._parse_yaml(data, file_name, mime_type, metadata)

            if ext in {".xml"}:
                return self._parse_xml(data, file_name, mime_type, metadata)

            if ext in {".eml"}:
                return self._parse_eml(data, file_name, mime_type, metadata)

            if ext in {".epub"}:
                return self._parse_epub(data, file_name, mime_type, metadata)

            if ext in {".png", ".jpg", ".jpeg", ".tiff", ".tif"}:
                return self._parse_image(data, file_name, mime_type, metadata)

            # Default fallback: try to decode as text
            text = self._decode_text_bytes(data)
            return [self._build_chunk(text, file_name, mime_type, metadata)]
        except Exception as exc:
            self.logger.error(f"Parsing failed for '{file_name}': {exc}")
            raise

    # --------------------------- Helpers ---------------------------
    def _build_chunk(
        self,
        content: str,
        source: str,
        mime_type: Optional[str],
        metadata: Dict[str, Any],
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        combined_meta = {"source": source, **(metadata or {})}
        if extra_meta:
            combined_meta.update(extra_meta)
        return {
            "content": content,
            "metadata": combined_meta,
            "source": source,
            "mime_type": mime_type,
        }

    def _decode_text_bytes(self, data: bytes) -> str:
        if chardet is not None:
            try:
                detected = chardet.detect(data) or {}
                enc = detected.get("encoding") or "utf-8"
                return data.decode(enc, errors="ignore")
            except Exception:
                pass
        # Fallback
        return data.decode("utf-8", errors="ignore")

    # --------------------------- Parsers ---------------------------
    def _parse_pdf(
        self, data: bytes, file_name: str, mime_type: Optional[str], metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        if pdfminer_high_level is None:
            raise ImportError("pdfminer.six is required to parse PDF files")
        extract_text = getattr(pdfminer_high_level, "extract_text", None)
        if extract_text is None:
            raise ImportError("pdfminer.high_level.extract_text not available")
        text = extract_text(io.BytesIO(data)) or ""
        return [self._build_chunk(text, file_name, mime_type, metadata)]

    def _parse_docx(
        self, data: bytes, file_name: str, mime_type: Optional[str], metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        if docx_module is None:
            raise ImportError("python-docx is required to parse DOCX files")
        doc = docx_module.Document(io.BytesIO(data))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
        text = "\n".join(paragraphs)
        return [self._build_chunk(text, file_name, mime_type, metadata)]

    def _parse_pptx(
        self, data: bytes, file_name: str, mime_type: Optional[str], metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        if pptx_module is None:
            raise ImportError("python-pptx is required to parse PPTX files")
        Presentation = getattr(pptx_module, "Presentation")
        prs = Presentation(io.BytesIO(data))
        chunks: List[Dict[str, Any]] = []
        for idx, slide in enumerate(prs.slides, start=1):
            lines: List[str] = []
            for shape in slide.shapes:
                text = None
                if hasattr(shape, "text_frame") and shape.text_frame is not None:
                    text = "\n".join([p.text for p in shape.text_frame.paragraphs if p.text])
                elif hasattr(shape, "text"):
                    text = getattr(shape, "text") or None
                if text:
                    lines.append(text)
            if lines:
                chunks.append(
                    self._build_chunk(
                        "\n".join(lines),
                        file_name,
                        mime_type,
                        metadata,
                        extra_meta={"slide": idx},
                    )
                )
        if not chunks:
            chunks.append(self._build_chunk("", file_name, mime_type, metadata))
        return chunks

    def _parse_csv(
        self, data: bytes, file_name: str, mime_type: Optional[str], metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        # Use pandas if available for robust CSV parsing
        if pandas_module is not None:
            try:
                import pandas as pd  # type: ignore
                from io import StringIO

                text = self._decode_text_bytes(data)
                df = pd.read_csv(StringIO(text))
                content = df.to_csv(index=False)
                return [self._build_chunk(content, file_name, mime_type, metadata)]
            except Exception:
                pass

        # Fallback: basic decoding
        text = self._decode_text_bytes(data)
        return [self._build_chunk(text, file_name, mime_type, metadata)]

    def _parse_xlsx(
        self, data: bytes, file_name: str, mime_type: Optional[str], metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        if pandas_module is None:
            raise ImportError("pandas + openpyxl are required to parse XLSX files")
        import pandas as pd  # type: ignore

        chunks: List[Dict[str, Any]] = []
        with pd.ExcelFile(io.BytesIO(data)) as xls:
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                content = df.to_csv(index=False)
                chunks.append(
                    self._build_chunk(
                        content,
                        file_name,
                        mime_type,
                        metadata,
                        extra_meta={"sheet": sheet_name},
                    )
                )
        return chunks

    def _parse_html(
        self, data: bytes, file_name: str, mime_type: Optional[str], metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        if bs4_module is None:
            raise ImportError("beautifulsoup4 is required to parse HTML files")
        from bs4 import BeautifulSoup  # type: ignore

        text = self._decode_text_bytes(data)
        soup = BeautifulSoup(text, "lxml") if _safe_import("lxml") else BeautifulSoup(text, "html.parser")
        extracted = soup.get_text("\n")
        return [self._build_chunk(extracted, file_name, mime_type, metadata)]

    def _parse_json(
        self, data: bytes, file_name: str, mime_type: Optional[str], metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        text = self._decode_text_bytes(data)
        try:
            obj = json.loads(text)
            flattened = self._flatten_json(obj)
            return [self._build_chunk(flattened, file_name, mime_type, metadata)]
        except Exception:
            return [self._build_chunk(text, file_name, mime_type, metadata)]

    def _parse_yaml(
        self, data: bytes, file_name: str, mime_type: Optional[str], metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        if yaml_module is None:
            text = self._decode_text_bytes(data)
            return [self._build_chunk(text, file_name, mime_type, metadata)]
        try:
            obj = yaml_module.safe_load(self._decode_text_bytes(data))  # type: ignore
            flattened = self._flatten_json(obj)
            return [self._build_chunk(flattened, file_name, mime_type, metadata)]
        except Exception:
            text = self._decode_text_bytes(data)
            return [self._build_chunk(text, file_name, mime_type, metadata)]

    def _parse_xml(
        self, data: bytes, file_name: str, mime_type: Optional[str], metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        if bs4_module is None:
            raise ImportError("beautifulsoup4 is required to parse XML files")
        from bs4 import BeautifulSoup  # type: ignore

        text = self._decode_text_bytes(data)
        soup = BeautifulSoup(text, "xml")
        extracted = soup.get_text("\n")
        return [self._build_chunk(extracted, file_name, mime_type, metadata)]

    def _parse_eml(
        self, data: bytes, file_name: str, mime_type: Optional[str], metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        msg = BytesParser(policy=policy.default).parsebytes(data)
        headers = {
            "subject": msg["subject"],
            "from": msg["from"],
            "to": msg["to"],
            "date": msg["date"],
        }
        parts: List[str] = []
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == "text/plain":
                    parts.append(part.get_content())
                elif ctype == "text/html":
                    html_text = part.get_content()
                    parts.append(self._html_to_text(html_text))
        else:
            ctype = msg.get_content_type()
            if ctype == "text/plain":
                parts.append(msg.get_content())
            elif ctype == "text/html":
                html_text = msg.get_content()
                parts.append(self._html_to_text(html_text))
        header_str = "\n".join([f"{k}: {v}" for k, v in headers.items() if v])
        body_str = "\n\n".join([p for p in parts if p])
        content = f"{header_str}\n\n{body_str}" if body_str else header_str
        return [self._build_chunk(content, file_name, mime_type, metadata)]

    def _parse_epub(
        self, data: bytes, file_name: str, mime_type: Optional[str], metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        if ebooklib_module is None or ebooklib_epub is None:
            raise ImportError("ebooklib is required to parse EPUB files")
        # Some versions of EbookLib expect a file path rather than a file-like object.
        # Persist to a temporary file for compatibility.
        import tempfile
        import os as _os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            book = ebooklib_epub.read_epub(tmp_path)  # type: ignore
        finally:
            try:
                _os.unlink(tmp_path)
            except Exception:
                pass
        texts: List[str] = []
        from bs4 import BeautifulSoup  # type: ignore

        for item in book.get_items():  # type: ignore
            try:
                # Prefer robust type check across versions
                if hasattr(ebooklib_epub, "EpubHtml") and isinstance(item, getattr(ebooklib_epub, "EpubHtml")):
                    html_text = item.get_content().decode("utf-8", errors="ignore")
                    soup = BeautifulSoup(html_text, "lxml") if _safe_import("lxml") else BeautifulSoup(html_text, "html.parser")
                    texts.append(soup.get_text("\n"))
                    continue
            except Exception:
                pass

            # Fallback: detect by name suffix
            get_name = getattr(item, "get_name", None)
            get_content = getattr(item, "get_content", None)
            if callable(get_name) and callable(get_content):
                name = (get_name() or "").lower()
                if name.endswith((".xhtml", ".html", ".htm")):
                    html_text = get_content().decode("utf-8", errors="ignore")
                    soup = BeautifulSoup(html_text, "lxml") if _safe_import("lxml") else BeautifulSoup(html_text, "html.parser")
                    texts.append(soup.get_text("\n"))
        content = "\n\n".join(texts)
        return [self._build_chunk(content, file_name, mime_type, metadata)]

    def _parse_image(
        self, data: bytes, file_name: str, mime_type: Optional[str], metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        if not self.ocr_enabled:
            self.logger.warning("OCR disabled; skipping text extraction from image")
            return [self._build_chunk("", file_name, mime_type, metadata)]
        if PIL_Image is None or pytesseract_module is None:
            raise ImportError("pytesseract and Pillow are required for OCR on images")
        image = PIL_Image.open(io.BytesIO(data))  # type: ignore
        text = pytesseract_module.image_to_string(image, lang=self.ocr_lang)  # type: ignore
        return [self._build_chunk(text, file_name, mime_type, metadata)]

    # --------------------------- Utilities ---------------------------
    def _flatten_json(self, obj: Any, prefix: str = "") -> str:
        lines: List[str] = []

        def _walk(o: Any, parent: str = "") -> None:
            if isinstance(o, dict):
                for k, v in o.items():
                    key = f"{parent}.{k}" if parent else str(k)
                    _walk(v, key)
            elif isinstance(o, list):
                for i, v in enumerate(o):
                    key = f"{parent}[{i}]" if parent else f"[{i}]"
                    _walk(v, key)
            else:
                lines.append(f"{parent}: {o}")

        _walk(obj, prefix)
        return "\n".join(lines)

    def _html_to_text(self, html_text: str) -> str:
        if bs4_module is None:
            return html_text
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(html_text, "lxml") if _safe_import("lxml") else BeautifulSoup(html_text, "html.parser")
        return soup.get_text("\n")


__all__ = ["DocumentParserService"]
