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
    <JST>2</JST><GV>2</GV>
  </Podmiot2>
  <Fa>
    <KodWaluty>PLN</KodWaluty><P_1>2026-10-14</P_1><P_6>2026-10-14</P_6><P_2>FV/1/2026</P_2>
    <P_13_1>100.00</P_13_1><P_14_1>23.00</P_14_1><P_15>123.00</P_15>
    <FaWiersz><NrWierszaFa>1</NrWierszaFa><P_7>Usługa &lt;hosting&gt;</P_7>
      <P_8A>szt.</P_8A><P_8B>1</P_8B><P_9A>100.00</P_9A><P_11>100.00</P_11><P_12>23</P_12>
    </FaWiersz>
    <Adnotacje><P_16>2</P_16><P_17>2</P_17><P_18>2</P_18><P_18A>2</P_18A>
      <Zwolnienie><P_19N>1</P_19N></Zwolnienie>
      <NoweSrodkiTransportu><P_22N>1</P_22N></NoweSrodkiTransportu>
      <P_23>2</P_23><PMarzy><P_PMarzyN>1</P_PMarzyN></PMarzy>
    </Adnotacje>
    <DodatkowyOpis><Klucz>Warunki</Klucz><Wartosc>Standardowe</Wartosc></DodatkowyOpis>
    <RodzajFaktury>VAT</RodzajFaktury>
  </Fa>
</Faktura>""".encode("utf-8")


def _with_payment(invoice_xml: bytes, payment_fields: str) -> bytes:
    payment = f"<Platnosc>{payment_fields}</Platnosc>".encode("utf-8")
    return invoice_xml.replace(b"</Fa>", payment + b"</Fa>")


def test_renders_supported_invoice_fields(invoice_xml: bytes) -> None:
    html = render_fa3_html(invoice_xml)
    assert '<html lang="pl">' in html
    assert "FV/1/2026" in html
    assert "2026-10-14" in html
    assert (
        "Data wystawienia:</strong> 2026-10-14<br><strong>Data dostawy lub wykonania usługi:</strong> 2026-10-14"
        in html
    )
    assert "Sprzedawca &amp; Syn" in html
    assert "Nabywca" in html
    assert "Usługa &lt;hosting&gt;" in html
    assert "100.00 PLN" in html
    assert "23%" in html
    assert "123.00 PLN" in html
    assert "<th>Nr wiersza</th>" in html
    assert "<td>1</td>" in html
    assert "Kwota należności ogółem</span><strong>123.00 PLN" in html
    assert "Dodatkowe informacje" in html
    assert "<dt>Warunki</dt><dd>Standardowe</dd>" in html


def test_legacy_call_matches_explicit_none(invoice_xml: bytes) -> None:
    assert render_fa3_html(invoice_xml) == render_fa3_html(
        invoice_xml, ksef_number=None
    )


def test_classic_template_preserves_legacy_default_and_is_deterministic(invoice_xml: bytes) -> None:
    legacy = render_fa3_html(invoice_xml)
    assert legacy == render_fa3_html(invoice_xml, template="default")
    classic = render_fa3_html(invoice_xml, template="classic", ksef_number="SYNTHETIC-12345678901234567890")
    assert classic == render_fa3_html(invoice_xml, template="classic", ksef_number="SYNTHETIC-12345678901234567890")
    assert 'font: 14px Arial' in classic
    assert "@page { size: A4; margin: 12mm; }" in classic
    assert "Numer KSeF:</strong> SYNTHETIC-12345678901234567890" in classic
    assert "Podsumowanie VAT" in classic and "Do zapłaty: 123,00 PLN" in classic
    assert "grid-template-columns" not in classic and "display: flex" not in classic


def test_classic_template_cli_selection(invoice_xml: bytes, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, output = tmp_path / "invoice.xml", tmp_path / "invoice.html"
    source.write_bytes(invoice_xml)
    monkeypatch.setattr(sys, "argv", ["render-doc", str(source), "--output", str(output), "--template", "classic"])
    assert main() == 0
    assert output.read_text(encoding="utf-8") == render_fa3_html(invoice_xml, template="classic")


def test_classic_template_escapes_untrusted_values(invoice_xml: bytes) -> None:
    altered = invoice_xml.replace(b"<P_7>Us\xc5\x82uga &lt;hosting&gt;</P_7>", b"<P_7>&lt;script&gt;alert(1)&lt;/script&gt;</P_7>")
    html = render_fa3_html(altered, template="classic", ksef_number="<script>")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "Numer KSeF:</strong> &lt;script&gt;" in html
    assert "<script>" not in html


def test_classic_template_handles_mixed_vat_and_long_values(invoice_xml: bytes) -> None:
    second_row = (
        b"<FaWiersz><NrWierszaFa>2</NrWierszaFa>"
        b"<P_7>" + (b"Opis pozycji " * 18) + b"</P_7>"
        b"<P_8B>2</P_8B><P_9A>50.00</P_9A><P_11>100.00</P_11><P_12>8</P_12></FaWiersz>"
    )
    altered = invoice_xml.replace(
        b"<P_13_1>100.00</P_13_1><P_14_1>23.00</P_14_1>",
        b"<P_13_1>100.00</P_13_1><P_14_1>23.00</P_14_1>"
        b"<P_13_2>100.00</P_13_2><P_14_2>8.00</P_14_2>",
    ).replace(b"<RodzajFaktury>VAT</RodzajFaktury>", second_row + b"<RodzajFaktury>VAT</RodzajFaktury>")
    altered = altered.replace(b"<Nazwa>Nabywca</Nazwa>", b"<Nazwa>" + (b"Dlugie imie firmy " * 12) + b"</Nazwa>")
    html = render_fa3_html(altered, template="classic", ksef_number="KSEF-" + "9" * 100)
    assert "Opis pozycji " in html and "8%" in html and "23%" in html
    assert "Dlugie imie firmy" in html and "9" * 100 in html
    assert "overflow-wrap: anywhere" in html
    assert "<script" not in html.lower() and "<link" not in html.lower()


def test_classic_template_formats_numbers_in_polish_without_changing_xml(
    invoice_xml: bytes,
) -> None:
    altered = invoice_xml.replace(
        b"<P_13_1>100.00</P_13_1><P_14_1>23.00</P_14_1><P_15>123.00</P_15>",
        b"<P_13_1>1234567.89</P_13_1><P_14_1>283950.6147</P_14_1>"
        b"<P_15>1518518.5047</P_15>",
    ).replace(b"<P_8B>1</P_8B>", b"<P_8B>12345.678</P_8B>")
    original = bytes(altered)

    html = render_fa3_html(altered, template="classic")

    assert "12\u00a0345,678 szt." in html
    assert "1\u00a0234\u00a0567,89 PLN" in html
    assert "283\u00a0950,6147 PLN" in html
    assert "1\u00a0518\u00a0518,5047 PLN" in html
    assert altered == original


def test_unknown_template_is_rejected(invoice_xml: bytes) -> None:
    with pytest.raises(ValueError, match="template must"):
        render_fa3_html(invoice_xml, template="unknown")


def test_invoice_without_payment_keeps_existing_output(invoice_xml: bytes) -> None:
    html = render_fa3_html(invoice_xml)

    assert "<section><h2>Płatność</h2>" not in html


def test_ksef_number_requires_text_or_none(invoice_xml: bytes) -> None:
    with pytest.raises(TypeError, match="ksef_number must be str or None"):
        render_fa3_html(invoice_xml, ksef_number=123)  # type: ignore[arg-type]


def test_renders_synthetic_ksef_number(invoice_xml: bytes) -> None:
    html = render_fa3_html(
        invoice_xml, ksef_number="5860000000-20261014-TEST"
    )

    assert (
        "<h2>Identyfikacja KSeF</h2><p><strong>Numer KSeF:</strong> "
        "5860000000-20261014-TEST</p>"
    ) in html


def test_ksef_number_is_escaped_as_untrusted_html(invoice_xml: bytes) -> None:
    html = render_fa3_html(
        invoice_xml,
        ksef_number='TEST<&"<script>alert(1)</script>',
    )

    assert "TEST&lt;&amp;&quot;&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>" not in html
    assert "alert(1)</script>" not in html


def test_ksef_number_rendering_is_deterministic_and_does_not_modify_xml(
    invoice_xml: bytes,
) -> None:
    original = bytes(invoice_xml)

    first = render_fa3_html(invoice_xml, ksef_number="SYNTHETIC-KSEF-001")
    second = render_fa3_html(invoice_xml, ksef_number="SYNTHETIC-KSEF-001")

    assert first == second
    assert invoice_xml == original


def test_renders_single_payment_term_and_required_connector_payment_form(
    invoice_xml: bytes,
) -> None:
    xml = _with_payment(
        invoice_xml,
        "<TerminPlatnosci><Termin>2026-11-02</Termin></TerminPlatnosci>"
        "<FormaPlatnosci>6</FormaPlatnosci>",
    )

    html = render_fa3_html(xml, ksef_number="SYNTHETIC-KSEF-001")

    assert "<strong>Termin płatności:</strong> 2026-11-02" in html
    assert "<strong>Forma płatności:</strong> Przelew" in html
    assert html.index("Termin płatności") < html.index("Forma płatności")
    assert "SYNTHETIC-KSEF-001" in html


def test_payment_term_without_form_is_supported_by_render_doc(
    invoice_xml: bytes,
) -> None:
    xml = _with_payment(
        invoice_xml,
        "<TerminPlatnosci><Termin>2026-11-02</Termin></TerminPlatnosci>",
    )

    html = render_fa3_html(xml)

    assert "<strong>Termin płatności:</strong> 2026-11-02" in html
    assert "Forma płatności" not in html


def test_renders_exempt_sales_with_multiple_rates_and_bank_account(
    invoice_xml: bytes,
) -> None:
    second_row = (
        b"<FaWiersz><NrWierszaFa>2</NrWierszaFa><P_7>Stawka 8</P_7>"
        b"<P_8B>1</P_8B><P_9A>50.00</P_9A><P_11>50.00</P_11><P_12>8</P_12></FaWiersz>"
    )
    exempt_row = (
        b"<FaWiersz><NrWierszaFa>3</NrWierszaFa><P_7>Zwolniona</P_7>"
        b"<P_8B>2</P_8B><P_9A>20.00</P_9A><P_11>40.00</P_11><P_12>zw</P_12></FaWiersz>"
    )
    xml = invoice_xml.replace(
        b"<P_13_1>100.00</P_13_1><P_14_1>23.00</P_14_1><P_15>123.00</P_15>",
        b"<P_13_1>100.00</P_13_1><P_14_1>23.00</P_14_1>"
        b"<P_13_2>50.00</P_13_2><P_14_2>4.00</P_14_2><P_13_7>40.00</P_13_7>"
        b"<P_15>217.00</P_15>",
    ).replace(
        b"<RodzajFaktury>VAT</RodzajFaktury>",
        second_row + exempt_row + b"<RodzajFaktury>VAT</RodzajFaktury>",
    )
    xml = _with_payment(
        xml,
        "<TerminPlatnosci><Termin>2026-11-02</Termin></TerminPlatnosci>"
        "<FormaPlatnosci>6</FormaPlatnosci>"
        "<RachunekBankowy><NrRB>1234567890</NrRB></RachunekBankowy>",
    )

    html = render_fa3_html(xml)

    assert html.index("<td>1</td>") < html.index("<td>2</td>") < html.index("<td>3</td>")
    assert "Zwolniona" in html
    assert "<td>zwolniona</td>" in html
    assert "Netto zwolniona</span><strong>40.00 PLN" in html
    assert "VAT zwolniona" not in html
    assert "Netto 8%</span><strong>50.00 PLN" in html
    assert "VAT 8%</span><strong>4.00 PLN" in html
    assert "Rachunek bankowy:</strong> 1234567890" in html
    assert "Kwota należności ogółem</span><strong>217.00 PLN" in html


@pytest.mark.parametrize(
    "account_xml",
    [
        "<RachunekBankowy/>",
        "<RachunekBankowy><NrRB>1234567890</NrRB><SWIFT>ABC</SWIFT></RachunekBankowy>",
        "<RachunekBankowy><NrRB>1234567890</NrRB></RachunekBankowy>"
        "<RachunekBankowy><NrRB>0987654321</NrRB></RachunekBankowy>",
    ],
)
def test_unsupported_bank_account_variants_are_rejected(
    invoice_xml: bytes, account_xml: str
) -> None:
    xml = _with_payment(
        invoice_xml,
        "<TerminPlatnosci><Termin>2026-11-02</Termin></TerminPlatnosci>"
        + account_xml,
    )

    with pytest.raises(UnsupportedDocumentError):
        render_fa3_html(xml)


@pytest.mark.parametrize("value", ["2026-02-30", "02.11.2026", "2026-1-02", ""])
def test_invalid_payment_term_date_is_rejected(
    invoice_xml: bytes, value: str
) -> None:
    xml = _with_payment(
        invoice_xml,
        f"<TerminPlatnosci><Termin>{value}</Termin></TerminPlatnosci>",
    )

    with pytest.raises(UnsupportedDocumentError, match="Termin.*(prawidłowej daty|puste)"):
        render_fa3_html(xml)


@pytest.mark.parametrize(
    "payment_fields",
    [
        "<Termin>2026-11-02</Termin>",
        "<TerminPlatnosci><Termin>2026-11-02</Termin>"
        "<TerminOpis><Ilosc>14</Ilosc></TerminOpis></TerminPlatnosci>",
        "<TerminPlatnosci><Termin>2026-11-02</Termin></TerminPlatnosci>"
        "<TerminPlatnosci><Termin>2026-11-03</Termin></TerminPlatnosci>",
        "<FormaPlatnosci>6</FormaPlatnosci>"
        "<TerminPlatnosci><Termin>2026-11-02</Termin></TerminPlatnosci>",
        "<Zaplacono>1</Zaplacono>"
        "<TerminPlatnosci><Termin>2026-11-02</Termin></TerminPlatnosci>",
        "<TerminPlatnosci><Termin>2026-11-02</Termin></TerminPlatnosci>"
        "<FormaPlatnosci>8</FormaPlatnosci>",
    ],
)
def test_unsupported_payment_variants_are_rejected(
    invoice_xml: bytes, payment_fields: str
) -> None:
    with pytest.raises(UnsupportedDocumentError):
        render_fa3_html(_with_payment(invoice_xml, payment_fields))


def test_payment_rendering_is_deterministic_and_does_not_modify_xml(
    invoice_xml: bytes,
) -> None:
    xml = _with_payment(
        invoice_xml,
        "<TerminPlatnosci><Termin>2026-11-02</Termin></TerminPlatnosci>"
        "<FormaPlatnosci>6</FormaPlatnosci>",
    )
    original = bytes(xml)

    first = render_fa3_html(xml, ksef_number="SYNTHETIC-KSEF-001")
    second = render_fa3_html(xml, ksef_number="SYNTHETIC-KSEF-001")

    assert first == second
    assert xml == original


def test_p6_is_rendered_even_when_equal_to_issue_date(invoice_xml: bytes) -> None:
    html = render_fa3_html(invoice_xml)
    assert "Data dostawy lub wykonania usługi:</strong> 2026-10-14" in html


@pytest.mark.parametrize("value", ["2026-02-30", "14.10.2026", "2026-1-01", ""])
def test_invalid_p6_date_is_rejected(invoice_xml: bytes, value: str) -> None:
    altered = invoice_xml.replace(
        b"<P_6>2026-10-14</P_6>", f"<P_6>{value}</P_6>".encode()
    )
    with pytest.raises(UnsupportedDocumentError, match="P_6.*(prawidłowej daty|puste)"):
        render_fa3_html(altered)


@pytest.mark.parametrize("element", [b"<P_6A>2026-10-14</P_6A>", b"<OkresFa/>"])
def test_unsupported_delivery_date_variants_are_rejected(
    invoice_xml: bytes, element: bytes
) -> None:
    altered = invoice_xml.replace(
        b"<RodzajFaktury>VAT</RodzajFaktury>",
        element + b"<RodzajFaktury>VAT</RodzajFaktury>",
    )
    with pytest.raises(UnsupportedDocumentError, match="P_6A|OkresFa"):
        render_fa3_html(altered)


@pytest.mark.parametrize(
    ("source", "replacement", "message"),
    [
        (b"<P_16>2</P_16>", b"<P_16>1</P_16>", "P_16"),
        (b"<P_19N>1</P_19N>", b"<P_19>1</P_19>", "P_19"),
        (b"<P_23>2</P_23>", b"<P_23>3</P_23>", "P_23"),
        (b"<P_23>2</P_23>", b"<Nieznane>2</Nieznane><P_23>2</P_23>", "Nieznane"),
    ],
)
def test_annotations_reject_active_unknown_or_invalid_values(
    invoice_xml: bytes, source: bytes, replacement: bytes, message: str
) -> None:
    with pytest.raises(UnsupportedDocumentError, match=message):
        render_fa3_html(invoice_xml.replace(source, replacement))


def test_additional_description_html_is_escaped(invoice_xml: bytes) -> None:
    altered = invoice_xml.replace(
        b"<Klucz>Warunki</Klucz><Wartosc>Standardowe</Wartosc>",
        b'<Klucz>&lt;script&gt;</Klucz><Wartosc>&lt;img src=x onerror=alert(1)&gt; &amp; "x"</Wartosc>',
    )
    html = render_fa3_html(altered)
    assert (
        "<dt>&lt;script&gt;</dt><dd>&lt;img src=x onerror=alert(1)&gt; &amp; &quot;x&quot;</dd>"
        in html
    )
    assert "<script>" not in html


def test_additional_descriptions_preserve_source_order(invoice_xml: bytes) -> None:
    second = (
        b"<DodatkowyOpis><Klucz>Drugi</Klucz><Wartosc>Wartosc</Wartosc></DodatkowyOpis>"
    )
    altered = invoice_xml.replace(
        b"<RodzajFaktury>VAT</RodzajFaktury>",
        second + b"<RodzajFaktury>VAT</RodzajFaktury>",
    )
    html = render_fa3_html(altered)
    assert html.index("<dt>Warunki</dt>") < html.index("<dt>Drugi</dt>")


@pytest.mark.parametrize(
    "extra",
    [b"<NrWiersza>1</NrWiersza>", b"<Nieznane>x</Nieznane>", b"<Klucz>x</Klucz>"],
)
def test_unsupported_additional_description_shapes_are_rejected(
    invoice_xml: bytes, extra: bytes
) -> None:
    altered = invoice_xml.replace(
        b"<Klucz>Warunki</Klucz><Wartosc>Standardowe</Wartosc>",
        b"<Klucz>Warunki</Klucz><Wartosc>Standardowe</Wartosc>" + extra,
    )
    with pytest.raises(UnsupportedDocumentError):
        render_fa3_html(altered)


def test_buyer_jst_and_gv_two_are_supported(invoice_xml: bytes) -> None:
    html = render_fa3_html(invoice_xml)
    assert "Nabywca" in html


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("JST", "1"),
        ("GV", "1"),
        ("JST", "3"),
        ("GV", "0"),
        ("JST", "invalid"),
        ("GV", "invalid"),
    ],
)
def test_unsupported_buyer_jst_or_gv_value_is_rejected(
    invoice_xml: bytes, field: str, value: str
) -> None:
    altered = invoice_xml.replace(
        f"<{field}>2</{field}>".encode(), f"<{field}>{value}</{field}>".encode()
    )
    with pytest.raises(UnsupportedDocumentError, match=f"wartość 2.*{field}"):
        render_fa3_html(altered)


@pytest.mark.parametrize("field", ["JST", "GV"])
def test_required_buyer_jst_or_gv_is_rejected_when_missing(
    invoice_xml: bytes, field: str
) -> None:
    altered = invoice_xml.replace(f"<{field}>2</{field}>".encode(), b"")
    with pytest.raises(UnsupportedDocumentError, match=f"Brak wymaganego pola {field}"):
        render_fa3_html(altered)


def test_podmiot3_is_rejected(invoice_xml: bytes) -> None:
    altered = invoice_xml.replace(b"  <Fa>", b"  <Podmiot3/><Fa>")
    with pytest.raises(UnsupportedDocumentError, match="Podmiot3"):
        render_fa3_html(altered)


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


def test_non_fa3_structure_remains_rejected_with_ksef_number() -> None:
    with pytest.raises(UnsupportedDocumentError, match="elementem Faktura"):
        render_fa3_html(b"<UPO/>", ksef_number="SYNTHETIC-KSEF-001")


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
    html_with_number = render_fa3_html(
        altered, ksef_number="SYNTHETIC-KSEF-001"
    )
    assert label in html
    assert f"Netto {label}</span><strong>100.00 PLN" in html
    if source_rate.startswith("0 "):
        assert "VAT 0%" not in html
    assert f"Netto {label}</span><strong>100.00 PLN" in html_with_number
    assert "Kwota należności ogółem</span><strong>123.00 PLN" in html_with_number


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


def test_exempt_rate_requires_p13_7_summary(invoice_xml: bytes) -> None:
    xml = invoice_xml.replace(b"<P_12>23</P_12>", b"<P_12>zw</P_12>")

    with pytest.raises(UnsupportedDocumentError, match="Brak wymaganych pól sumarycznych.*zwolniona"):
        render_fa3_html(xml)


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
