"""Tests for KSeF KOD I: exact source bytes, QR, safety, API and CLI."""

from __future__ import annotations

from base64 import b64decode, urlsafe_b64encode
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
import socket

from PIL import Image
import pytest

from render_doc import KsefVerification, render_fa3_html
from render_doc.ksef_verification import _verification_panel, _verification_url
from render_doc.ksef_template import render_ksef_template


@pytest.fixture
def data():
    return {
        "number": "SYN/2026/001", "issue_date": "2026-11-09",
        "delivery_date": "", "seller": "Sprzedawca (NIP: 1234567890)",
        "seller_address": ["Gdynia"], "buyer": "Nabywca (NIP: 1234567891)",
        "buyer_address": ["Warszawa"], "gross": "123.00", "currency": "PLN",
        "payment_due_date": "", "payment_form": "", "bank_account": "",
    }


@pytest.mark.parametrize("environment,host", [
    ("TEST", "https://qr-test.ksef.mf.gov.pl"),
    ("DEMO", "https://qr-demo.ksef.mf.gov.pl"),
    ("PROD", "https://qr.ksef.mf.gov.pl"),
])
def test_official_kod_i_link_uses_exact_xml_bytes(environment, host):
    xml = b"<Faktura> \x00 fake but hashable </Faktura>\n"
    digest = urlsafe_b64encode(sha256(xml).digest()).rstrip(b"=").decode("ascii")
    assert _verification_url(
        xml, seller_nip="1234567890", issue_date="2026-11-09",
        environment=environment,
    ) == f"{host}/invoice/1234567890/09-11-2026/{digest}"


def test_url_layout_matches_official_spec_example():
    url = _verification_url(
        b"abc", seller_nip="1111111111", issue_date="2026-02-01",
        environment="TEST",
    )
    assert url.startswith(
        "https://qr-test.ksef.mf.gov.pl/invoice/1111111111/01-02-2026/"
    )
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", url.rsplit("/", 1)[-1])


def test_xml_canonicalization_is_not_used():
    original = b"<x/>"
    first = _verification_url(
        original, seller_nip="1234567890",
        issue_date="2026-11-09", environment="DEMO",
    )
    second = _verification_url(
        b"<x />", seller_nip="1234567890",
        issue_date="2026-11-09", environment="DEMO",
    )
    assert first != second and original == b"<x/>"


def test_qr_is_offline_inline_png_and_same_link(data, monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Network is forbidden in rendering")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    xml = b"<?xml version='1.0'?><Faktura/>"
    metadata = KsefVerification("DEMO", "1234567890-20261109-SYNTHETIC")
    panel = _verification_panel(xml, data, metadata)
    assert "ŚRODOWISKO DEMO" in panel
    assert metadata.ksef_number in panel
    match = re.search(r'src="data:image/png;base64,([A-Za-z0-9+/=]+)"', panel)
    assert match is not None
    png = b64decode(match.group(1))
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    image = Image.open(BytesIO(png))
    assert image.format == "PNG" and image.width == image.height
    expected = _verification_url(
        xml, seller_nip="1234567890", issue_date="2026-11-09",
        environment="DEMO",
    )
    assert f'href="{expected}"' in panel
    assert 'rel="noopener noreferrer"' in panel
    assert panel.count(expected) == 2


def test_png_scans_to_exact_same_kod_i_url_when_decoder_available(data):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    xml = b"<synthetic/>"
    panel = _verification_panel(
        xml, data, KsefVerification("TEST", "1234567890-20261109-SYNTHETIC")
    )
    png = b64decode(re.search(
        r'src="data:image/png;base64,([A-Za-z0-9+/=]+)"', panel
    ).group(1))
    decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(
        cv2.imdecode(np.frombuffer(png, dtype=np.uint8), cv2.IMREAD_COLOR)
    )
    assert decoded == _verification_url(
        xml, seller_nip="1234567890", issue_date="2026-11-09",
        environment="TEST",
    )


@pytest.mark.parametrize("metadata", [
    ("LIVE", "1234567890-20261109-TEST"),
    ("prod", "1234567890-20261109-TEST"),
    ("", "1234567890-20261109-TEST"),
    ("DEMO", ""),
    ("PROD", "<script>alert(1)</script>"),
    ("TEST", "KSEF Number with spaces"),
    ("TEST", "x" * 101),
])
def test_rejects_untrusted_metadata(metadata):
    with pytest.raises(ValueError):
        KsefVerification(*metadata)


def test_rejects_bad_seller_or_issue_date():
    with pytest.raises(ValueError, match="NIP"):
        _verification_url(
            b"abc", seller_nip="1/2345", issue_date="2026-11-09",
            environment="TEST",
        )
    with pytest.raises(ValueError, match="date"):
        _verification_url(
            b"abc", seller_nip="1234567890", issue_date="2026-02-30",
            environment="TEST",
        )
    with pytest.raises(TypeError):
        _verification_url(
            "xml", seller_nip="1234567890",
            issue_date="2026-11-09", environment="TEST",
        )


def test_qr_identical_on_repetition_and_escapes_by_construction(data):
    meta = KsefVerification("TEST", "1234567890-20261109-SYNTHETIC")
    a = _verification_panel(b"<same />", data, meta)
    b = _verification_panel(b"<same />", data, meta)
    assert a == b
    assert not any(token in a.lower() for token in ("<script", "onerror=", "onclick="))


def test_qr_missing_or_invalid_identity_fails_closed(data):
    with pytest.raises(TypeError):
        _verification_panel(b"abc", data, "DEMO")
    data["seller"] = "Seller (NIP: <script>)"
    with pytest.raises(ValueError, match="NIP"):
        _verification_panel(
            b"abc", data, KsefVerification("DEMO", "1234567890-20261109-SYNTHETIC")
        )


def test_ksef_template_legacy_html_has_no_qr(data):
    rows = [{"number": "1", "description": "Synthetic", "unit": "szt.",
             "quantity": "1.00", "unit_net": "100.00", "net": "100.00",
             "tax_rate": "23%"}]
    summary = [{"rate": "23%", "net": "100.00", "vat": "23.00"}]
    raw = render_ksef_template(data, rows, summary, [], "SYNTHETIC")
    assert "data:image" not in raw and 'href="' not in raw
    panel = _verification_panel(
        b"<x/>", data, KsefVerification("TEST", "1234567890-20261109-SYNTHETIC")
    )
    html = render_ksef_template(
        data, rows, summary, [], "1234567890-20261109-SYNTHETIC",
        verification_panel=panel,
    )
    assert "data:image/png;base64," in html
    assert "123,00 PLN" in html
    assert "KSeF" in html


_CASES = [
    "01-jedna-pozycja-vat-23",
    "02-mieszane-stawki-vat",
    "03-wiele-pozycji-dlugie-opisy-i-nazwy",
    "04-przelew-termin-rachunek",
    "05-warianty-vat-zero",
]


@pytest.mark.parametrize("name", _CASES)
def test_public_api_qr_only_when_explicitly_enabled(name):
    xml = (
        Path(__file__).resolve().parents[1]
        / "docs/examples/classic" / f"{name}.xml"
    ).read_bytes()
    default = render_fa3_html(xml)
    classic = render_fa3_html(xml, template="classic")
    previous = render_fa3_html(xml, template="ksef", ksef_number="SYNTHETIC")
    assert default == render_fa3_html(xml, template="default")
    assert classic == render_fa3_html(xml, template="classic")
    assert "data:image/png" not in default + classic + previous
    meta = KsefVerification("DEMO", "0000000000-20261109-SYNTHETIC")
    html = render_fa3_html(xml, template="ksef", verification=meta)
    assert 'src="data:image/png;base64,' in html
    assert 'href="https://qr-demo.ksef.mf.gov.pl/invoice/0000000000/' in html
    assert "ŚRODOWISKO DEMO" in html
    assert "SYNTHETIC" in html


def test_public_api_rejects_mismatch_or_unsupported_template():
    xml = (
        Path(__file__).resolve().parents[1]
        / "docs/examples/classic/01-jedna-pozycja-vat-23.xml"
    ).read_bytes()
    meta = KsefVerification("TEST", "0000000000-20261109-SYNTHETIC")
    with pytest.raises(ValueError, match="ksef"):
        render_fa3_html(xml, template="default", verification=meta)
    with pytest.raises(ValueError, match="mismatch"):
        render_fa3_html(
            xml, template="ksef", ksef_number="DIFFERENT", verification=meta,
        )
    with pytest.raises(TypeError):
        render_fa3_html(xml, template="ksef", verification="TEST")


def test_cli_explicit_qr_options(monkeypatch, tmp_path):
    from render_doc.cli import main

    fixture = (
        Path(__file__).resolve().parents[1]
        / "docs/examples/classic/01-jedna-pozycja-vat-23.xml"
    )
    output = tmp_path / "preview.html"
    monkeypatch.setattr("sys.argv", [
        "render-doc", str(fixture), "--output", str(output),
        "--template", "ksef", "--qr-environment", "TEST",
        "--ksef-number", "0000000000-20261109-SYNTHETIC",
    ])
    assert main() == 0
    assert "data:image/png;base64," in output.read_text(encoding="utf-8")


def test_cli_rejects_incomplete_qr_metadata(monkeypatch, tmp_path):
    from render_doc.cli import main

    fixture = (
        Path(__file__).resolve().parents[1]
        / "docs/examples/classic/01-jedna-pozycja-vat-23.xml"
    )
    monkeypatch.setattr("sys.argv", [
        "render-doc", str(fixture), "--output", str(tmp_path / "out.html"),
        "--template", "ksef", "--qr-environment", "PROD",
    ])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
