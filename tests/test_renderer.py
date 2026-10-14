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
    assert "<th>Nr wiersza</th>" in html
    assert "<td>1</td>" in html
    assert "Kwota należności ogółem</span><strong>123.00 PLN" in html


def test_preserves_source_line_number_and_escapes_it(invoice_xml: bytes) -> None:
    altered = invoice_xml.replace(
        b"<NrWierszaFa>1</NrWierszaFa>",
        b"<NrWierszaFa>7&lt;8</NrWierszaFa>",
    )
    html = render_fa3_html(altered)
    assert "<td>7&lt;8</td>" in html
    assert "<td>1</td>" not in html


def test_optional_unit_is_rendered_or_shown_as_dash(invoice_xml: bytes) -> None:
    with_unit = render_fa3_html(invoice_xml)
    assert "<td>1 szt.</td>" in with_unit

    without_unit = render_fa3_html(invoice_xml.replace(b"<P_8A>szt.</P_8A>", b""))
    assert "<td>1 —</td>" in without_unit
    assert "<td>1 </td>" not in without_unit


def test_summary_uses_source_totals_and_p15(invoice_xml: bytes) -> None:
    html = render_fa3_html(invoice_xml)
    assert "Netto 23%</span><strong>100.00 PLN" in html
    assert "VAT 23%</span><strong>23.00 PLN" in html
    assert "Kwota należności ogółem</span><strong>123.00 PLN" in html


def test_invalid_xml_has_readable_exception() -> None:
    with pytest.raises(InvalidXmlError, match="Nie można odczytać"):
        render_fa3_html(b"<Faktura>")


def test_non_fa3_structure_is_rejected() -> None:
    with pytest.raises(UnsupportedDocumentError, match="elementem Faktura"):
        render_fa3_html(b"<UPO/>")


def test_mixed_vat_rows_and_summary_are_rendered(invoice_xml: bytes) -> None:
    second_row = """<FaWiersz><NrWierszaFa>3</NrWierszaFa><P_7>Stawka obniżona</P_7>
      <P_8A>szt.</P_8A><P_8B>1</P_8B><P_9A>50.00</P_9A><P_11>50.00</P_11><P_12>8</P_12></FaWiersz>""".encode()
    altered = invoice_xml.replace(
        b"<P_13_1>100.00</P_13_1><P_14_1>23.00</P_14_1>",
        b"<P_13_1>100.00</P_13_1><P_14_1>23.00</P_14_1>"
        b"<P_13_2>50.00</P_13_2><P_14_2>4.00</P_14_2>",
    ).replace(
        b"<RodzajFaktury>VAT</RodzajFaktury>",
        second_row + b"<RodzajFaktury>VAT</RodzajFaktury>",
    )
    html = render_fa3_html(altered)
    assert "23%" in html
    assert "8%" in html
    assert "Netto 23%</span><strong>100.00 PLN" in html
    assert "VAT 23%</span><strong>23.00 PLN" in html
    assert "Netto 8%</span><strong>50.00 PLN" in html
    assert "VAT 8%</span><strong>4.00 PLN" in html


@pytest.mark.parametrize(
    ("source_rate", "label", "net_field"),
    [
        ("23", "23%", "P_13_1"),
        ("8", "8%", "P_13_2"),
        ("5", "5%", "P_13_3"),
        ("0 KR", "0% (krajowa)", "P_13_6_1"),
        ("0 WDT", "0% (WDT)", "P_13_6_2"),
        ("0 EX", "0% (eksport)", "P_13_6_3"),
    ],
)
def test_supported_rates_and_zero_rate_variants(
    invoice_xml: bytes, source_rate: str, label: str, net_field: str
) -> None:
    altered = invoice_xml.replace(
        b"<P_12>23</P_12>", f"<P_12>{source_rate}</P_12>".encode()
    )
    if source_rate != "23":
        altered = altered.replace(b"<P_13_1>100.00</P_13_1><P_14_1>23.00</P_14_1>", b"")
        summary = f"<{net_field}>100.00</{net_field}>"
        tax_field = {"8": "P_14_2", "5": "P_14_3"}.get(source_rate)
        if tax_field:
            summary += f"<{tax_field}>{source_rate}.00</{tax_field}>"
        altered = altered.replace(b"<P_15>", f"{summary}<P_15>".encode())
    html = render_fa3_html(altered)
    assert label in html
    assert f"Netto {label}</span><strong>100.00 PLN" in html
    if source_rate.startswith("0 "):
        assert "VAT 0%" not in html


def test_multiple_rows_preserve_xml_order_and_source_numbers(
    invoice_xml: bytes,
) -> None:
    row = b"""<FaWiersz><NrWierszaFa>42</NrWierszaFa><P_7>Druga &amp; &lt;b&gt;pozycja&lt;/b&gt;</P_7>
      <P_8A>opak.</P_8A><P_8B>2</P_8B><P_9A>10.00</P_9A><P_11>20.00</P_11><P_12>23</P_12></FaWiersz>"""
    altered = invoice_xml.replace(
        b"<RodzajFaktury>VAT</RodzajFaktury>",
        row + b"<RodzajFaktury>VAT</RodzajFaktury>",
    )
    html = render_fa3_html(altered)
    assert html.index("<td>1</td>") < html.index("<td>42</td>")
    assert "Druga &amp; &lt;b&gt;pozycja&lt;/b&gt;" in html
    assert "<td>2 opak.</td>" in html
    assert "<td>20.00 PLN</td>" in html


def test_unsupported_rate_is_rejected(invoice_xml: bytes) -> None:
    with pytest.raises(UnsupportedDocumentError, match="Nieobsługiwana stawka VAT"):
        render_fa3_html(invoice_xml.replace(b"<P_12>23</P_12>", b"<P_12>7</P_12>"))


def test_missing_required_summary_field_is_rejected(invoice_xml: bytes) -> None:
    altered = invoice_xml.replace(b"<P_14_1>23.00</P_14_1>", b"")
    with pytest.raises(UnsupportedDocumentError, match="Niepełne podsumowanie VAT"):
        render_fa3_html(altered)


def test_ambiguous_zero_rate_is_rejected(invoice_xml: bytes) -> None:
    altered = invoice_xml.replace(b"<P_12>23</P_12>", b"<P_12>0</P_12>")
    with pytest.raises(UnsupportedDocumentError, match="Nieobsługiwana stawka VAT"):
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
