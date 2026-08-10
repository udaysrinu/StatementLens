"""PdfDecryptor + PdfTextExtractor — concrete adapters for the Decryptor / TextExtractor ports.

Heavy deps (pikepdf, pdfplumber) are imported lazily so the package imports without them; the
optional [pdf] extra installs them. Password candidates come from crypto.password_rules.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List

from . import password_rules


class PdfDecryptError(RuntimeError):
    pass


class PdfDecryptor:
    """Decrypts a password-protected PDF by trying derived candidate passwords (Decryptor port)."""

    def decrypt(self, data: bytes, hints: Dict[str, Any]) -> bytes:
        try:
            import pikepdf
        except ImportError as e:  # pragma: no cover
            raise PdfDecryptError("pikepdf not installed (pip install 'statementlens[pdf]')") from e

        # not encrypted? return unchanged
        try:
            with pikepdf.open(io.BytesIO(data)):
                return data
        except pikepdf.PasswordError:
            pass

        passwords: List[str] = password_rules.candidates(hints)
        for pw in passwords:
            try:
                with pikepdf.open(io.BytesIO(data), password=pw) as pdf:
                    out = io.BytesIO()
                    pdf.save(out)
                    return out.getvalue()
            except pikepdf.PasswordError:
                continue
        raise PdfDecryptError(
            f"could not unlock PDF with {len(passwords)} candidate password(s); "
            "provide better hints (name/dob/mobile/card_last4) or an explicit 'custom' password")


class PdfTextExtractor:
    """Extracts text from a decrypted PDF (TextExtractor port)."""

    def extract(self, data: bytes) -> str:
        try:
            import pdfplumber
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("pdfplumber not installed (pip install 'statementlens[pdf]')") from e
        parts: List[str] = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return "\n".join(parts)
