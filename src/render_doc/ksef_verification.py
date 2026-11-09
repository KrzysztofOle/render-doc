"""Offline KSeF KOD I URL and QR image for an accepted FA(3) invoice.

The caller supplies the confirmed KSeF number and the environment explicitly.
No KSeF lookup or assertion of authenticity is made by this module.
"""

from __future__ import annotations

from base64 import b64encode, urlsafe_b64encode
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from html import escape
from io import BytesIO
import re

import qrcode
from qrcode.constants import ERROR_CORRECT_M


_ENVIRONMENTS = {
    "TEST": "https://qr-test.ksef.mf.gov.pl",
    "DEMO": "https://qr-demo.ksef.mf.gov.pl",
    "PROD": "https://qr.ksef.mf.gov.pl",
}


@dataclass(frozen=True)
class KsefVerification:
    """Caller-attested accepted invoice metadata, NOT an online verification.

    The environment must be TEST, DEMO or PROD. The caller MUST obtain the
    KSeF number from a trustworthy receipt/query and pass original FA(3)
    XML bytes unchanged to render_fa3_html.
    """

    environment: str
    ksef_number: str

    def __post_init__(self) -> None:
        if not isinstance(self.environment, str) or self.environment not in _ENVIRONMENTS:
            raise ValueError("KSeF QR environment must be TEST, DEMO or PROD.")
        if (not isinstance(self.ksef_number, str)
                or re.fullmatch(r"[A-Za-z0-9-]{1,100}", self.ksef_number) is None):
            raise ValueError("KSeF QR requires a non-empty, safe, caller-confirmed KSeF number.")


def _verification_url(
    original_xml: bytes, *, seller_nip: str, issue_date: str, environment: str
) -> str:
    """KOD I link per CIRF/MF; digest exact XML bytes, never reserialize."""
    if not isinstance(original_xml, bytes):
        raise TypeError("original_xml must be bytes")
    if re.fullmatch(r"[0-9]{10}", seller_nip) is None:
        raise ValueError("KSeF QR requires a 10-digit seller NIP in FA(3).")
    try:
        issued = date.fromisoformat(issue_date)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid FA(3) issue date for KSeF QR.") from exc
    if issued.isoformat() != issue_date:
        raise ValueError("Invalid FA(3) issue date format for KSeF QR.")
    if environment not in _ENVIRONMENTS:
        raise ValueError("Unsupported KSeF QR environment.")
    digest = urlsafe_b64encode(sha256(original_xml).digest()).rstrip(b"=").decode("ascii")
    return (
        f"{_ENVIRONMENTS[environment]}/invoice/{seller_nip}/"
        f"{issued:%d-%m-%Y}/{digest}"
    )


def _verification_panel(
    original_xml: bytes, data: dict[str, object], verification: KsefVerification
) -> str:
    """Build a self-contained, printable QR section with an HTTPS link."""
    if not isinstance(verification, KsefVerification):
        raise TypeError("verification must be a KsefVerification instance")

    seller = data["seller"]
    if not isinstance(seller, str):
        raise ValueError("Seller identity is missing from parsed FA(3).")
    _, separator, suffix = seller.rpartition(" (NIP: ")
    if not separator or not suffix.endswith(")"):
        raise ValueError("Seller NIP is missing from parsed FA(3).")
    seller_nip = suffix[:-1]
    url = _verification_url(
        original_xml,
        seller_nip=seller_nip,
        issue_date=str(data["issue_date"]),
        environment=verification.environment,
    )

    qr = qrcode.QRCode(
        version=None, error_correction=ERROR_CORRECT_M, box_size=6, border=4
    )
    qr.add_data(url, optimize=0)
    qr.make(fit=True)
    output = BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(output, format="PNG")
    png = b64encode(output.getvalue()).decode("ascii")
    safe_number = escape(verification.ksef_number, quote=True)
    safe_url = escape(url, quote=True)
    env_label = (
        '<p class="verification-environment">ŚRODOWISKO TESTOWE — dokument demonstracyjny</p>'
        if verification.environment == "TEST"
        else '<p class="verification-environment">ŚRODOWISKO DEMO — dokument demonstracyjny</p>'
        if verification.environment == "DEMO"
        else ""
    )
    return (
        '<section class="section verification" aria-label="Weryfikacja faktury w KSeF">'
        '<h2 class="section-title">Kod weryfikujący KSeF</h2>'
        f'{env_label}'
        '<div class="verification-grid">'
        '<div class="verification-qr">'
        f'<img class="qr-image" src="data:image/png;base64,{png}" '
        'alt="Kod QR KOD I do sprawdzenia faktury w KSeF">'
        f'<div class="qr-label">{safe_number}</div>'
        '</div>'
        '<div class="verification-info">'
        '<p>Zeskanuj kod lub otwórz link, aby sprawdzić fakturę w systemie KSeF.</p>'
        f'<a href="{safe_url}" rel="noopener noreferrer">{safe_url}</a>'
        '<p class="verification-hint">Sam kod QR nie jest dowodem przyjęcia '
        'faktury przez KSeF; numer musi pochodzić z potwierdzonego odbioru.</p>'
        '</div></div></section>'
    )
