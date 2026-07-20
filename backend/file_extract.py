"""
Extracts plain text from an uploaded file so it can be run through the
same detector used for pasted text. Supports .txt, .pdf, and .docx.
"""
import io


class ExtractionError(Exception):
    pass


def extract_text(file_storage) -> str:
    """file_storage: a Werkzeug FileStorage object (from request.files)."""
    filename = (file_storage.filename or "").lower()
    raw = file_storage.read()

    if filename.endswith(".txt"):
        return raw.decode("utf-8", errors="ignore").strip()

    if filename.endswith(".pdf"):
        try:
            import pdfplumber
        except ImportError:
            raise ExtractionError("pdfplumber is not installed. Run: pip install pdfplumber")
        try:
            text_parts = []
            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text_parts.append(page_text)
            text = "\n".join(text_parts).strip()
            if not text:
                raise ExtractionError(
                    "No selectable text found in this PDF. It may be a scanned image — "
                    "try a text-based PDF, or paste the text directly instead."
                )
            return text
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"Could not read PDF: {e}")

    if filename.endswith(".docx"):
        try:
            import docx
        except ImportError:
            raise ExtractionError("python-docx is not installed. Run: pip install python-docx")
        try:
            doc = docx.Document(io.BytesIO(raw))
            text = "\n".join(p.text for p in doc.paragraphs).strip()
            if not text:
                raise ExtractionError("No text found in this .docx file.")
            return text
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"Could not read .docx file: {e}")

    raise ExtractionError("Unsupported file type. Please upload a .txt, .pdf, or .docx file.")
