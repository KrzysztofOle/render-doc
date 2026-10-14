"""Tests for the public FA(3) HTML rendering API.

Tests (EN):
- Exercise a synthetic supported invoice and unsafe or unsupported inputs.

Testy (PL):
- Sprawdzają syntetyczną fakturę oraz niebezpieczne i nieobsługiwane dane.

File: tests/test_renderer.py
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

from render_doc.cli import main
from render_doc.renderer import (
    InvalidXmlError,
    UnsupportedDocumentError,
    render_fa3_html,
)


@pytest.fixture
def invoice_xml() -> bytes:
    return """<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="http://crd.gov.pl/wzor/2025/06/25/13775/">
  <Naglowek>
    <KodFormularza kodSystemowy="FA (3)" wersjaSchemy="1-0E">FA</KodFormularza>
    <WariantFormularza>3</WariantFormularza>
    <DataWytworzeniaFa>2026-10-14T10:00:00Z</DataWytworzeniaFa>
  </Naglowek>
  <Podmiot1>
    <DaneIdentyfikacyjne><NIP>1111111111</NIP><Nazwa>Sprzedawca &amp; Syn</Nazwa></DaneIdentyfikacyjne>
    <Adres><KodKraju>PL</KodKraju><AdresL1>Przykładowa 1, 00-001 Warszawa</AdresL1></Adres>
  </Podmiot1>
  <Podmiot2>
    <DaneIdentyfikacyjne><NIP>2222222222</NIP><Nazwa>Nabywca</Nazwa></DaneIdentyfikacyjne>
    <Adres><KodKraju>PL</KodKraju><AdresL1>Testowa 2, 00-002 Łódź</AdresL1></Adres>
  </Podmiot2>
  <Fa>
    <KodWaluty>PLN</KodWaluty><P_1>2026-10-14</P_1><P_2>FV/1/2026</P_2>
    <P_13_1>100.00</P_13_1><P_14_1>23.00</P_14_1><P_15>123.00</P_15>
    <FaWiersz><NrWierszaFa>1</NrWierszaFa><P_7>Usługa &lt;hosting&gt;</P_7>
      <P_8A>szt.</P_8A><P_8B>1</P_8B><P_9A>100.00</P_9A><P_11>100.00</P_11><P_12>23</P_12>
    </FaWiersz>
    <RodzajFaktury>VAT</RodzajFaktury>
  </Fa>
</Faktura>""".encode("utf-8")


def test_renders_supported_invoice_fields(invoice_xml: bytes) -> None:
    html = render_fa3_html(invoice_xml)
    assert '<html lang="pl">' in html
    assert "FV/1/2026" in html
    assert "2026-10-14" in html
    assert "Sprzedawca &amp; Syn" in html
    assert "Nabywca" in html
    assert "Usługa &lt;hosting&gt;" in html
    assert "100.00 PLN" in html
    assert "23%" in html
    assert "123.00 PLN" in html


def test_invalid_xml_has_readable_exception() -> None:
    with pytest.raises(InvalidXmlError, match="Nie można odczytać"):
        render_fa3_html(b"<Faktura>")


def test_non_fa3_structure_is_rejected() -> None:
    with pytest.raises(UnsupportedDocumentError, match="elementem Faktura"):
        render_fa3_html(b"<UPO/>")


def test_unsupported_vat_profile_is_rejected(invoice_xml: bytes) -> None:
    altered = invoice_xml.replace(b"<P_12>23</P_12>", b"<P_12>8</P_12>")
    with pytest.raises(UnsupportedDocumentError, match="stawka VAT 23%"):
        render_fa3_html(altered)


def test_external_entity_declaration_is_rejected(tmp_path: Path) -> None:
    secret = tmp_path / "external.txt"
    secret.write_text("nie wolno wczytać", encoding="utf-8")
    xml = (
        f'<!DOCTYPE Faktura [<!ENTITY xxe SYSTEM "{secret.as_uri()}">]>'
        "<Faktura>&xxe;</Faktura>"
    ).encode()
    with pytest.raises(InvalidXmlError, match="DTD"):
        render_fa3_html(xml)


def test_html_special_characters_are_escaped(invoice_xml: bytes) -> None:
    html = render_fa3_html(invoice_xml)
    assert "Sprzedawca &amp; Syn" in html
    assert "Usługa &lt;hosting&gt;" in html
    assert "<hosting>" not in html


def test_output_is_deterministic(invoice_xml: bytes) -> None:
    assert render_fa3_html(invoice_xml) == render_fa3_html(invoice_xml)


def test_cli_output_matches_api(
    tmp_path: Path, invoice_xml: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "input.xml"
    output = tmp_path / "output.html"
    source.write_bytes(invoice_xml)
    monkeypatch.setattr(
        sys, "argv", ["render-doc", str(source), "--output", str(output)]
    )
    assert main() == 0
    assert output.read_text(encoding="utf-8") == render_fa3_html(invoice_xml)


def test_input_bytes_are_not_modified(invoice_xml: bytes) -> None:
    original = bytes(invoice_xml)
    render_fa3_html(invoice_xml)
    assert invoice_xml == original


def test_html_has_no_external_resources_or_scripts(invoice_xml: bytes) -> None:
    html = render_fa3_html(invoice_xml)
    assert "<script" not in html.lower()
    assert "<link" not in html.lower()
    assert "src=" not in html.lower()
    assert "url(" not in html.lower()


def test_rendering_does_not_open_network_connections(
    invoice_xml: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("renderowanie nie może otwierać połączeń sieciowych")

    monkeypatch.setattr(socket.socket, "connect", fail_connect)
    monkeypatch.setattr(socket, "create_connection", fail_connect)
    render_fa3_html(invoice_xml)
