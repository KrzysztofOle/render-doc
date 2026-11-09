"""Targeted tests of the opt-in KSeF-inspired HTML template.

Features (EN):
- Verifies source field fidelity, safe HTML, print layout and determinism.

Funkcje (PL):
- Weryfikuje dane źródłowe, bezpieczny HTML, druk oraz determinizm.

File: tests/test_ksef_template.py
"""

from __future__ import annotations

from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path

import pytest

from render_doc.ksef_template import render_ksef_template


@pytest.fixture
def invoice_data() -> dict[str, object]:
    return {
        "number": "SYN/2026/001",
        "issue_date": "2026-10-14",
        "delivery_date": "2026-10-14",
        "seller": "Przykładowy Sprzedawca Sp. z o.o. (NIP: 0000000000)",
        "seller_address": ["PL", "ul. Przykładowa 1", "80-100 Gdańsk"],
        "buyer": "Testowy Nabywca (NIP: 0000000001)",
        "buyer_address": ["PL", "ul. Testowa 2", "00-100 Warszawa"],
        "gross": "123.00",
        "currency": "PLN",
        "payment_due_date": "2026-11-14",
        "payment_form": "Przelew",
        "bank_account": "11 1111 1111 1111 1111 1111 1111",
    }


@pytest.fixture
def invoice_rows() -> list[dict[str, str]]:
    return [
        {
            "number": "1",
            "description": "Usługa testowa",
            "unit": "szt.",
            "quantity": "1.00",
            "unit_net": "100.00",
            "net": "100.00",
            "tax_rate": "23%",
        }
    ]


@pytest.fixture
def vat_summary() -> list[dict[str, str | None]]:
    return [{"rate": "23%", "net": "100.00", "vat": "23.00"}]


def _render(data, rows, summary, extra=None, number=None) -> str:
    return render_ksef_template(data, rows, summary, extra or [], number)


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.attrs: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag, attrs):
        self.attrs.append((tag, dict(attrs)))


def test_ksef_template_contains_accounting_fields_and_is_a4(
    invoice_data, invoice_rows, vat_summary
) -> None:
    result = _render(invoice_data, invoice_rows, vat_summary,
                     [{"key": "Zamówienie", "value": "XYZ/12"}], "SYNTHETIC-KSEF-NUMBER")
    for expected in (
        "<!doctype html>", "lang=\"pl\"", "Krajowy System e-Faktur",
        "SYN/2026/001", "14.10.2026", "Numer KSeF:",
        "Przykładowy Sprzedawca Sp. z o.o.", "NIP:", "0000000000",
        "Testowy Nabywca", "Usługa testowa", "100,00", "23,00",
        "123,00", "PLN", "Przelew", "14.11.2026", "Rachunek bankowy",
        "Zamówienie", "XYZ/12", "@page { size: A4",
        "thead { display: table-header-group; }",
    ):
        assert expected in result
    assert result.startswith("<!doctype html>")
    assert result.endswith("</html>\n")


def test_ksef_template_does_not_modify_inputs_and_is_deterministic(
    invoice_data, invoice_rows, vat_summary
) -> None:
    inputs = (invoice_data, invoice_rows, vat_summary)
    before = deepcopy(inputs)
    a = _render(*inputs, number="SYNTHETIC-KSEF-NUMBER")
    b = _render(*inputs, number="SYNTHETIC-KSEF-NUMBER")
    assert a == b
    assert inputs == before


def test_untrusted_content_is_escaped_and_no_external_resources(
    invoice_data, invoice_rows, vat_summary
) -> None:
    invoice_data["number"] = '<img src="https://bad.invalid/x" onerror="alert(1)">'
    invoice_rows[0]["description"] = "</td><script>alert(1)</script> & test"
    result = _render(invoice_data, invoice_rows, vat_summary,
                     [{"key": "x", "value": "<b>secret</b>"}], "<script>evil</script>")
    assert "&lt;script&gt;" in result
    assert "&lt;img src=&quot;" in result
    assert "&lt;b&gt;secret&lt;/b&gt;" in result
    assert "<script" not in result and "<img" not in result
    parsed = _Links()
    parsed.feed(result)
    assert not any(tag in ("script", "img", "iframe", "link") for tag, _ in parsed.attrs)
    assert not any("src" in attrs or "href" in attrs for _, attrs in parsed.attrs)


@pytest.mark.parametrize("rate", ["0 KR", "0 WDT", "0 EX", "zw"])
def test_zero_and_exempt_gross_are_source_net(rate, invoice_data, invoice_rows):
    summary = [{"rate": rate, "net": "1999.50", "vat": None}]
    result = _render(invoice_data, invoice_rows, summary)
    assert "1\u00a0999,50" in result
    assert rate in result
    assert "—" in result


def test_gross_uses_source_tax_sum_without_rounding(invoice_data, invoice_rows):
    summary = [{"rate": "23%", "net": "112.345", "vat": "25.83935"}]
    result = _render(invoice_data, invoice_rows, summary)
    assert "138,18435" in result
    assert "112,345" in result and "25,83935" in result
    assert "123,00" in result  # P_15 is not replaced by computed VAT gross.


def test_empty_payment_and_extra_do_not_create_empty_tables(invoice_data, invoice_rows, vat_summary):
    invoice_data.update(payment_due_date="", payment_form="", bank_account="")
    result = _render(invoice_data, invoice_rows, vat_summary)
    assert '<table class="payments"' not in result
    assert '<table class="extra"' not in result
    assert "Numer KSeF" not in result
    assert "<svg" not in result and "data:image" not in result


def test_long_invoice_rows_are_kept(invoice_data, invoice_rows, vat_summary):
    invoice_rows[0]["description"] = "Bardzo długa nazwa " * 30
    invoice_rows *= 40
    for i, item in enumerate(invoice_rows, start=1):
        item["number"] = str(i)
    result = _render(invoice_data, invoice_rows, vat_summary)
    assert result.count('class="description"') == 40
    assert "Bardzo długa nazwa " * 30 in result
    assert "break-inside: avoid" in result


@pytest.mark.parametrize("name", [
    "01-jedna-pozycja-vat-23",
    "02-mieszane-stawki-vat",
    "03-wiele-pozycji-dlugie-opisy-i-nazwy",
    "04-przelew-termin-rachunek",
    "05-warianty-vat-zero",
])
def test_public_api_renders_existing_synthetic_examples(name):
    """Run against the actual parser only in the full render-doc checkout."""
    from render_doc import render_fa3_html

    folder = Path(__file__).resolve().parents[1] / "docs/examples/classic"
    xml = (folder / f"{name}.xml").read_bytes()
    default = render_fa3_html(xml)
    assert default == render_fa3_html(xml, template="default")
    classic = render_fa3_html(xml, template="classic")
    assert classic == render_fa3_html(xml, template="classic")
    rendered = render_fa3_html(xml, template="ksef", ksef_number="SYNTHETIC")
    assert rendered.startswith("<!doctype html>")
    assert "SYNTHETIC" in rendered
    assert "Numer faktury" in rendered
    assert "@page { size: A4" in rendered
    assert "<script" not in rendered
    assert "<img" not in rendered


def test_cli_supports_ksef_template(monkeypatch, tmp_path):
    """The CLI must expose the new template only as explicit opt-in."""
    from render_doc.cli import main
    from render_doc import render_fa3_html

    folder = Path(__file__).resolve().parents[1] / "docs/examples/classic"
    xml = (folder / "01-jedna-pozycja-vat-23.xml").read_bytes()
    source = tmp_path / "invoice.xml"
    target = tmp_path / "preview.html"
    source.write_bytes(xml)
    monkeypatch.setattr("sys.argv", [
        "render-doc", str(source), "--output", str(target), "--template", "ksef"
    ])
    assert main() == 0
    assert target.read_text(encoding="utf-8") == render_fa3_html(xml, template="ksef")
