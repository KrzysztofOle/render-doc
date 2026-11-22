"""Compare supported FA(3) source fields with their rendered HTML locations.

Features (EN):
- Independently extracts expected accounting data from original XML fixtures.
- Checks that each value is rendered in the correct semantic HTML section.

Funkcje (PL):
- Niezależnie odczytuje oczekiwane dane księgowe z oryginalnych fixture XML.
- Sprawdza przypisanie wartości do właściwych sekcji HTML.

File: tests/test_source_html_consistency.py
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from typing import ClassVar
from xml.etree import ElementTree

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from render_doc import (
    InvalidXmlError,
    UnsupportedDocumentError,
    render_fa3_html,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "docs" / "examples" / "classic"
NAMESPACE = "http://crd.gov.pl/wzor/2025/06/25/13775/"
NS = {"fa": NAMESPACE}
VAT_RATES = {
    "23": ("23%", "P_13_1", "P_14_1"),
    "8": ("8%", "P_13_2", "P_14_2"),
    "5": ("5%", "P_13_3", "P_14_3"),
    "0 KR": ("0% (krajowa)", "P_13_6_1", None),
    "0 WDT": ("0% (WDT)", "P_13_6_2", None),
    "0 EX": ("0% (eksport)", "P_13_6_3", None),
    "zw": ("zwolniona", "P_13_7", None),
}
PAYMENT_FORMS = {
    "1": "Gotówka",
    "2": "Karta",
    "3": "Bon",
    "4": "Czek",
    "5": "Kredyt",
    "6": "Przelew",
    "7": "Mobilna",
}
EXAMPLE_NAMES = (
    "01-jedna-pozycja-vat-23",
    "02-mieszane-stawki-vat",
    "03-wiele-pozycji-dlugie-opisy-i-nazwy",
    "04-przelew-termin-rachunek",
    "05-warianty-vat-zero",
)


@dataclass
class _Node:
    tag: str
    attrs: dict[str, str | None]
    parent: _Node | None = None
    children: list[_Node | str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "".join(
            child if isinstance(child, str) else child.text for child in self.children
        )

    def descendants(self, tag: str | None = None) -> list[_Node]:
        found: list[_Node] = []
        for child in self.children:
            if isinstance(child, _Node):
                if tag is None or child.tag == tag:
                    found.append(child)
                found.extend(child.descendants(tag))
        return found

    def first(self, tag: str) -> _Node:
        matches = self.descendants(tag)
        assert matches, f"Brak elementu HTML <{tag}>"
        return matches[0]


class _DocumentParser(HTMLParser):
    """Build the small HTML tree needed to assert semantic data placement."""

    _VOID: ClassVar[set[str]] = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("#document", {})
        self.stack = [self.root]
        self.malformed = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = _Node(tag, dict(attrs), self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in self._VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack[-1].children.append(_Node(tag, dict(attrs), self.stack[-1]))

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                if index != len(self.stack) - 1:
                    self.malformed = True
                del self.stack[index:]
                return
        self.malformed = True

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


def _parse_html(html: str) -> _Node:
    parser = _DocumentParser()
    parser.feed(html)
    parser.close()
    assert not parser.malformed and len(parser.stack) == 1
    return parser.root


def _class_nodes(root: _Node, class_name: str) -> list[_Node]:
    return [
        node
        for node in root.descendants()
        if class_name in (node.attrs.get("class") or "").split()
    ]


def _source_text(
    parent: ElementTree.Element, path: str, *, required: bool = True
) -> str:
    node = parent.find(path, NS)
    if node is None or node.text is None:
        assert not required, f"Brak oczekiwanego źródłowego pola {path}"
        return ""
    return node.text.strip()


def _pl_number(value: str) -> str:
    number = Decimal(value)
    places = max(0, -number.as_tuple().exponent)
    return f"{number:,.{places}f}".replace(",", "\u00a0").replace(".", ",")


def _pl_date(value: str) -> str:
    return date.fromisoformat(value).strftime("%d.%m.%Y")


def _assert_party(
    root: _Node, invoice_xml: ElementTree.Element, party_name: str, label: str
) -> None:
    party = invoice_xml.find(f"fa:{party_name}", NS)
    assert party is not None
    identity = party.find("fa:DaneIdentyfikacyjne", NS)
    assert identity is not None
    cards = [
        node
        for node in _class_nodes(root, "party-card")
        if node.first("h2").text == label
    ]
    assert len(cards) == 1
    card = cards[0]
    assert _class_nodes(card, "party-name")[0].text == _source_text(
        identity, "fa:Nazwa"
    )
    assert (
        _class_nodes(card, "party-nip")[0].text
        == f"NIP: {_source_text(identity, 'fa:NIP')}"
    )
    addresses = party.findall("fa:Adres", NS)
    expected_address = []
    for address in addresses:
        for field_name in ("KodKraju", "AdresL1", "AdresL2"):
            value = _source_text(address, f"fa:{field_name}", required=False)
            if value:
                expected_address.append(value)
    assert [
        node.text for node in _class_nodes(card, "party-address")
    ] == expected_address


def assert_supported_source_matches_ksef_html(xml_bytes: bytes, html: str) -> None:
    """Compare source values independently with their expected HTML sections."""
    source = ElementTree.fromstring(xml_bytes)
    root = _parse_html(html)
    invoice = source.find("fa:Fa", NS)
    assert invoice is not None

    assert _class_nodes(root, "invoice-number")[0].text == _source_text(
        invoice, "fa:P_2"
    )
    details = _class_nodes(root, "details")
    assert len(details) == 1
    detail_values = {
        child.first("span").text: child.descendants("span")[-1].text
        for child in details[0].descendants("div")
        if len(child.descendants("span")) >= 2
    }
    assert detail_values.get("Data wystawienia") == _pl_date(
        _source_text(invoice, "fa:P_1")
    )
    assert detail_values.get("Waluta") == _source_text(invoice, "fa:KodWaluty")
    delivery_date = _source_text(invoice, "fa:P_6", required=False)
    assert detail_values.get("Data dostawy lub wykonania usługi", "") == (
        _pl_date(delivery_date) if delivery_date else ""
    )

    _assert_party(root, source, "Podmiot1", "Sprzedawca")
    _assert_party(root, source, "Podmiot2", "Nabywca")

    items = _class_nodes(root, "items")
    assert len(items) == 1
    actual_rows = [row for row in items[0].descendants("tr") if row.descendants("td")]
    source_rows = invoice.findall("fa:FaWiersz", NS)
    assert len(actual_rows) == len(source_rows)
    for source_row, actual_row in zip(source_rows, actual_rows, strict=True):
        cells = actual_row.descendants("td")
        assert len(cells) == 7
        rate = _source_text(source_row, "fa:P_12")
        expected_rate = VAT_RATES[rate][0]
        expected = (
            _source_text(source_row, "fa:NrWierszaFa"),
            _source_text(source_row, "fa:P_7"),
            _pl_number(_source_text(source_row, "fa:P_8B")),
            _source_text(source_row, "fa:P_8A", required=False) or "—",
            _pl_number(_source_text(source_row, "fa:P_9A")),
            expected_rate,
            _pl_number(_source_text(source_row, "fa:P_11")),
        )
        assert tuple(cell.text for cell in cells) == expected

    summaries: list[tuple[str, str, str, str]] = []
    seen_rates = {_source_text(row, "fa:P_12") for row in source_rows}
    for source_rate, (label, net_field, tax_field) in VAT_RATES.items():
        net = _source_text(invoice, f"fa:{net_field}", required=False)
        if not net:
            assert source_rate not in seen_rates
            continue
        tax = (
            _source_text(invoice, f"fa:{tax_field}", required=False)
            if tax_field
            else ""
        )
        gross = str(Decimal(net) + Decimal(tax)) if tax else net
        summaries.append((label, _pl_number(net), _pl_number(tax) if tax else "—", _pl_number(gross)))
    summary_tables = _class_nodes(root, "vat-summary")
    assert len(summary_tables) == 1
    summary_rows = [
        row for row in summary_tables[0].descendants("tr") if row.descendants("td")
    ]
    assert len(summary_rows) == len(summaries)
    for row, expected in zip(summary_rows, summaries, strict=True):
        cells = row.descendants("td")
        assert tuple(cell.text for cell in cells) == expected

    amount_due = _class_nodes(root, "amount-due")
    assert len(amount_due) == 1
    assert amount_due[0].text.endswith(
        f"{_pl_number(_source_text(invoice, 'fa:P_15'))} {_source_text(invoice, 'fa:KodWaluty')}"
    )

    payment = invoice.find("fa:Platnosc", NS)
    actual_payment = _class_nodes(root, "payments")
    if payment is None:
        assert not actual_payment
    else:
        payment_expected = []
        term = payment.find("fa:TerminPlatnosci/fa:Termin", NS)
        if term is not None and term.text:
            payment_expected.append(("Termin płatności", _pl_date(term.text.strip())))
        form = payment.find("fa:FormaPlatnosci", NS)
        if form is not None and form.text:
            payment_expected.append(
                ("Forma płatności", PAYMENT_FORMS[form.text.strip()])
            )
        account = payment.find("fa:RachunekBankowy/fa:NrRB", NS)
        if account is not None and account.text:
            payment_expected.append(("Rachunek bankowy", account.text.strip()))
        actual = []
        for row in actual_payment[0].descendants("tr") if actual_payment else []:
            cells = row.descendants("td")
            actual.append((cells[0].text, cells[1].text))
        assert actual == payment_expected

    extra_nodes = invoice.findall("fa:DodatkowyOpis", NS)
    extra_tables = _class_nodes(root, "extra")
    if extra_nodes:
        assert len(extra_tables) == 1
        expected_extra = [
            (_source_text(node, "fa:Klucz"), _source_text(node, "fa:Wartosc"))
            for node in extra_nodes
        ]
        actual_extra = [
            tuple(cell.text for cell in row.descendants("td"))
            for row in extra_tables[0].descendants("tr")
        ]
        assert actual_extra == expected_extra
    else:
        assert not extra_tables


def _check_pair(xml_path: Path, html_path: Path) -> tuple[str, str]:
    """Return a safe status and reason code for one local document pair."""
    try:
        xml_bytes = xml_path.read_bytes()
        html = html_path.read_text(encoding="utf-8")
    except OSError:
        return "FAIL", "INPUT_READ_ERROR"
    except UnicodeError:
        return "FAIL", "HTML_ENCODING_ERROR"

    try:
        # Reuse production profile qualification, while comparing only against
        # independently extracted source values and the caller's HTML.
        render_fa3_html(xml_bytes, template="ksef")
    except UnsupportedDocumentError:
        return "UNSUPPORTED", "PROFILE_UNSUPPORTED"
    except InvalidXmlError:
        return "FAIL", "XML_INVALID"
    try:
        assert_supported_source_matches_ksef_html(xml_bytes, html)
    except (AssertionError, ElementTree.ParseError, IndexError):
        return "FAIL", "HTML_MISMATCH"
    return "PASS", "SOURCE_FIELDS_MATCH"


def _offline_main() -> int:
    parser = argparse.ArgumentParser(
        description="Prywatna, lokalna kontrola pary XML FA(3) i HTML ksef."
    )
    parser.add_argument("--xml", required=True, type=Path)
    parser.add_argument("--html", required=True, type=Path)
    args = parser.parse_args()
    status, reason = _check_pair(args.xml, args.html)
    print(f"{status} {reason}")
    return {"PASS": 0, "FAIL": 1, "UNSUPPORTED": 2}[status]


@pytest.mark.parametrize("name", EXAMPLE_NAMES)
def test_ksef_html_preserves_accounting_fields_by_source_section(name: str) -> None:
    xml_bytes = (EXAMPLES / f"{name}.xml").read_bytes()
    html = render_fa3_html(xml_bytes, template="ksef")
    assert_supported_source_matches_ksef_html(xml_bytes, html)


def _example_with_rate(rate: str) -> bytes:
    """Adapt the existing one-row fixture to a supported VAT category."""
    xml_bytes = (EXAMPLES / f"{EXAMPLE_NAMES[0]}.xml").read_bytes()
    if rate == "5":
        return xml_bytes.replace(
            b"<P_13_1>100.00</P_13_1><P_14_1>23.00</P_14_1><P_15>123.00</P_15>",
            b"<P_13_3>100.00</P_13_3><P_14_3>5.00</P_14_3><P_15>105.00</P_15>",
        ).replace(b"<P_12>23</P_12>", b"<P_12>5</P_12>")
    if rate == "zw":
        return xml_bytes.replace(
            b"<P_13_1>100.00</P_13_1><P_14_1>23.00</P_14_1><P_15>123.00</P_15>",
            b"<P_13_7>100.00</P_13_7><P_15>100.00</P_15>",
        ).replace(b"<P_12>23</P_12>", b"<P_12>zw</P_12>")
    raise AssertionError(f"Unsupported test rate: {rate}")


@pytest.mark.parametrize("rate", ("5", "zw"))
def test_ksef_html_preserves_supported_special_rate_by_source(rate: str) -> None:
    xml_bytes = _example_with_rate(rate)
    html = render_fa3_html(xml_bytes, template="ksef")
    assert_supported_source_matches_ksef_html(xml_bytes, html)


def test_detects_changed_vat_5_amount_in_vat_summary() -> None:
    xml_bytes = _example_with_rate("5")
    html = render_fa3_html(xml_bytes, template="ksef")
    table = re.search(r'(<table class="vat-summary">.*?</table>)', html, re.DOTALL)
    assert table is not None
    changed, count = re.subn(
        r'(<tbody>.*?<td class="number">)5,00(</td>)',
        r"\g<1>6,00\g<2>",
        table.group(0),
        count=1,
        flags=re.DOTALL,
    )
    assert count == 1
    with pytest.raises(AssertionError):
        assert_supported_source_matches_ksef_html(
            xml_bytes, html.replace(table.group(0), changed, 1)
        )


def test_detects_changed_exempt_sales_in_vat_summary() -> None:
    xml_bytes = _example_with_rate("zw")
    html = render_fa3_html(xml_bytes, template="ksef")
    table = re.search(r'(<table class="vat-summary">.*?</table>)', html, re.DOTALL)
    assert table is not None
    changed, count = re.subn(
        r'(<tbody>.*?<td class="number">)100,00(</td>)',
        r"\g<1>101,00\g<2>",
        table.group(0),
        count=1,
        flags=re.DOTALL,
    )
    assert count == 1
    with pytest.raises(AssertionError):
        assert_supported_source_matches_ksef_html(
            xml_bytes, html.replace(table.group(0), changed, 1)
        )


def _assert_mutation_rejected(
    xml_bytes: bytes, html: str, original: str, changed: str
) -> None:
    assert html.count(original) == 1
    with pytest.raises(AssertionError):
        assert_supported_source_matches_ksef_html(
            xml_bytes, html.replace(original, changed, 1)
        )


def test_detects_changed_nip_in_party_section() -> None:
    xml_bytes = (EXAMPLES / f"{EXAMPLE_NAMES[0]}.xml").read_bytes()
    html = render_fa3_html(xml_bytes, template="ksef")
    _assert_mutation_rejected(xml_bytes, html, "0000000000", "9999999999")


def test_detects_wrong_vat_amount_in_vat_summary() -> None:
    xml_bytes = (EXAMPLES / f"{EXAMPLE_NAMES[0]}.xml").read_bytes()
    html = render_fa3_html(xml_bytes, template="ksef")
    table = re.search(r'(<table class="vat-summary">.*?</table>)', html, re.DOTALL)
    assert table is not None
    changed, count = re.subn(
        r'(<tbody>.*?<td class="number">)23,00(</td>)',
        r"\g<1>24,00\g<2>",
        table.group(0),
        count=1,
        flags=re.DOTALL,
    )
    assert count == 1
    with pytest.raises(AssertionError):
        assert_supported_source_matches_ksef_html(
            xml_bytes, html.replace(table.group(0), changed, 1)
        )


def test_detects_missing_invoice_row() -> None:
    xml_bytes = (EXAMPLES / f"{EXAMPLE_NAMES[2]}.xml").read_bytes()
    html = render_fa3_html(xml_bytes, template="ksef")
    row = re.search(
        r"<tr>(?:(?!</tr>).)*Wdrozenie systemu etap pierwszy(?:(?!</tr>).)*</tr>", html
    )
    assert row is not None
    with pytest.raises(AssertionError):
        assert_supported_source_matches_ksef_html(
            xml_bytes, html.replace(row.group(0), "", 1)
        )


def test_detects_substituted_invoice_row_amount() -> None:
    xml_bytes = (EXAMPLES / f"{EXAMPLE_NAMES[2]}.xml").read_bytes()
    html = render_fa3_html(xml_bytes, template="ksef")
    row = re.search(
        r"<tr>(?:(?!</tr>).)*Wdrozenie systemu etap pierwszy(?:(?!</tr>).)*</tr>", html
    )
    assert row is not None
    changed_row = row.group(0).replace(">125,00</td>", ">126,00</td>", 1)
    assert changed_row != row.group(0)
    with pytest.raises(AssertionError):
        assert_supported_source_matches_ksef_html(
            xml_bytes, html.replace(row.group(0), changed_row, 1)
        )


def test_detects_missing_source_bank_account() -> None:
    xml_bytes = (EXAMPLES / f"{EXAMPLE_NAMES[3]}.xml").read_bytes()
    html = render_fa3_html(xml_bytes, template="ksef")
    account = "00001234567890123456789012"
    assert account in html
    with pytest.raises(AssertionError):
        assert_supported_source_matches_ksef_html(
            xml_bytes, html.replace(account, "", 1)
        )


def test_detects_data_assigned_to_wrong_party_section() -> None:
    xml_bytes = (EXAMPLES / f"{EXAMPLE_NAMES[0]}.xml").read_bytes()
    html = render_fa3_html(xml_bytes, template="ksef")
    cards = re.findall(
        r'(<div class="party-card"><h2>(?:Sprzedawca|Nabywca)</h2>)(.*?)(</div>)',
        html,
        re.DOTALL,
    )
    assert len(cards) == 2
    seller, buyer = cards
    assert "0000000000" in seller[1] and "0000000001" in buyer[1]
    swapped_html = html.replace(
        "".join(seller), "".join((seller[0], buyer[1], seller[2])), 1
    ).replace("".join(buyer), "".join((buyer[0], seller[1], buyer[2])), 1)
    assert "0000000000" in swapped_html and "0000000001" in swapped_html
    with pytest.raises(AssertionError):
        assert_supported_source_matches_ksef_html(xml_bytes, swapped_html)


def test_rejects_unsupported_invoice_type_instead_of_partial_render() -> None:
    xml_bytes = (EXAMPLES / f"{EXAMPLE_NAMES[0]}.xml").read_bytes()
    unsupported = xml_bytes.replace(
        b"<RodzajFaktury>VAT</RodzajFaktury>",
        b"<RodzajFaktury>KOR</RodzajFaktury>",
    )
    with pytest.raises(UnsupportedDocumentError):
        render_fa3_html(unsupported, template="ksef")


@pytest.mark.parametrize(
    ("name", "rate"),
    [(name, None) for name in EXAMPLE_NAMES]
    + [(EXAMPLE_NAMES[0], rate) for rate in ("5", "zw")],
)
def test_offline_pair_check_classifies_supported_examples(
    tmp_path: Path, name: str, rate: str | None
) -> None:
    xml_bytes = (EXAMPLES / f"{name}.xml").read_bytes()
    if rate is not None:
        xml_bytes = _example_with_rate(rate)
    xml_path = tmp_path / "source.xml"
    html_path = tmp_path / "offline-pair.html"
    xml_path.write_bytes(xml_bytes)
    html_path.write_text(render_fa3_html(xml_bytes, template="ksef"), encoding="utf-8")
    assert _check_pair(xml_path, html_path) == ("PASS", "SOURCE_FIELDS_MATCH")


def test_offline_pair_check_fails_safely_for_changed_data(tmp_path: Path) -> None:
    xml_bytes = (EXAMPLES / f"{EXAMPLE_NAMES[0]}.xml").read_bytes()
    html = render_fa3_html(xml_bytes, template="ksef").replace(
        "0000000000", "9999999999", 1
    )
    xml_path = tmp_path / "synthetic.xml"
    html_path = tmp_path / "synthetic.html"
    xml_path.write_bytes(xml_bytes)
    html_path.write_text(html, encoding="utf-8")
    assert _check_pair(xml_path, html_path) == ("FAIL", "HTML_MISMATCH")


@pytest.mark.parametrize(
    ("name", "old", "new"),
    (
        (EXAMPLE_NAMES[0], "0000000000", "9999999999"),
        (EXAMPLE_NAMES[0], "123,00 PLN", "124,00 PLN"),
        (EXAMPLE_NAMES[3], "00001234567890123456789012", "00001234567890123456789013"),
        (EXAMPLE_NAMES[0], "Standardowe", "Usunięto"),
    ),
)
def test_offline_pair_check_rejects_mutated_html(
    tmp_path: Path, name: str, old: str, new: str
) -> None:
    xml_bytes = (EXAMPLES / f"{name}.xml").read_bytes()
    html = render_fa3_html(xml_bytes, template="ksef")
    assert html.count(old) == 1
    xml_path = tmp_path / "pair.xml"
    html_path = tmp_path / "pair.html"
    xml_path.write_bytes(xml_bytes)
    html_path.write_text(html.replace(old, new, 1), encoding="utf-8")
    assert _check_pair(xml_path, html_path) == ("FAIL", "HTML_MISMATCH")


def test_offline_pair_check_classifies_invalid_and_missing_inputs(
    tmp_path: Path,
) -> None:
    xml_path = tmp_path / "broken.xml"
    html_path = tmp_path / "page.html"
    xml_path.write_text("<broken", encoding="utf-8")
    html_path.write_text("<html></html>", encoding="utf-8")
    assert _check_pair(xml_path, html_path) == ("FAIL", "XML_INVALID")
    assert _check_pair(tmp_path / "missing.xml", html_path) == (
        "FAIL",
        "INPUT_READ_ERROR",
    )


def test_offline_pair_check_rejects_malformed_html(tmp_path: Path) -> None:
    xml_path = EXAMPLES / f"{EXAMPLE_NAMES[0]}.xml"
    html_path = tmp_path / "malformed.html"
    html_path.write_text("<html><body></html>", encoding="utf-8")
    assert _check_pair(xml_path, html_path) == ("FAIL", "HTML_MISMATCH")


@pytest.mark.parametrize("label", ("Data wystawienia", "Waluta", "Numer faktury"))
def test_offline_pair_check_fails_for_missing_required_html_field(
    tmp_path: Path, label: str
) -> None:
    xml_path = EXAMPLES / f"{EXAMPLE_NAMES[0]}.xml"
    html = render_fa3_html(xml_path.read_bytes(), template="ksef")
    if label == "Numer faktury":
        pattern = r'<div class="invoice-number">.*?</div>'
    else:
        pattern = (
            rf'<div><span class="detail-label">{re.escape(label)}</span>'
            r'<span class="detail-value">.*?</span></div>'
        )
    mutated_html, count = re.subn(pattern, "", html, count=1)
    assert count == 1
    pair_xml_path = tmp_path / "source.xml"
    pair_html_path = tmp_path / "missing-field.html"
    pair_xml_path.write_bytes(xml_path.read_bytes())
    pair_html_path.write_text(mutated_html, encoding="utf-8")
    assert _check_pair(pair_xml_path, pair_html_path) == (
        "FAIL",
        "HTML_MISMATCH",
    )


def test_offline_pair_check_classifies_unsupported_profile(tmp_path: Path) -> None:
    xml_bytes = (
        (EXAMPLES / f"{EXAMPLE_NAMES[0]}.xml")
        .read_bytes()
        .replace(
            b"<RodzajFaktury>VAT</RodzajFaktury>",
            b"<RodzajFaktury>KOR</RodzajFaktury>",
        )
    )
    xml_path = tmp_path / "unsupported.xml"
    html_path = tmp_path / "page.html"
    xml_path.write_bytes(xml_bytes)
    html_path.write_text("<html></html>", encoding="utf-8")
    assert _check_pair(xml_path, html_path) == (
        "UNSUPPORTED",
        "PROFILE_UNSUPPORTED",
    )


def test_offline_pair_check_classifies_unknown_field_as_unsupported(
    tmp_path: Path,
) -> None:
    xml_bytes = (
        (EXAMPLES / f"{EXAMPLE_NAMES[0]}.xml")
        .read_bytes()
        .replace(b"</Fa>", b"<NieznanePole>synthetic</NieznanePole></Fa>")
    )
    xml_path = tmp_path / "unknown.xml"
    html_path = tmp_path / "page.html"
    xml_path.write_bytes(xml_bytes)
    html_path.write_text("<html></html>", encoding="utf-8")
    assert _check_pair(xml_path, html_path) == (
        "UNSUPPORTED",
        "PROFILE_UNSUPPORTED",
    )


def _run_offline_cli(
    xml_path: Path, html_path: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--xml",
            str(xml_path),
            "--html",
            str(html_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_offline_cli_prints_only_safe_status(tmp_path: Path) -> None:
    xml_path = EXAMPLES / f"{EXAMPLE_NAMES[0]}.xml"
    html_path = tmp_path / "rendered.html"
    html_path.write_text(
        render_fa3_html(xml_path.read_bytes(), template="ksef"), encoding="utf-8"
    )
    result = _run_offline_cli(xml_path, html_path)
    assert result.returncode == 0
    assert result.stdout == "PASS SOURCE_FIELDS_MATCH\n"
    assert not result.stderr

    html_path.write_text(
        html_path.read_text(encoding="utf-8").replace("0000000000", "9999999999", 1),
        encoding="utf-8",
    )
    failed = _run_offline_cli(xml_path, html_path)
    assert failed.returncode == 1
    assert failed.stdout == "FAIL HTML_MISMATCH\n"
    assert not failed.stderr


@pytest.mark.parametrize("label", ("Data wystawienia", "Waluta"))
def test_offline_cli_missing_html_fields_fail_without_data_leaks(
    tmp_path: Path, label: str
) -> None:
    xml_path = EXAMPLES / f"{EXAMPLE_NAMES[0]}.xml"
    html = render_fa3_html(xml_path.read_bytes(), template="ksef")
    pattern = (
        rf'<div><span class="detail-label">{re.escape(label)}</span>'
        r'<span class="detail-value">.*?</span></div>'
    )
    mutated_html, count = re.subn(pattern, "", html, count=1)
    assert count == 1
    html_path = tmp_path / "missing-field.html"
    html_path.write_text(mutated_html, encoding="utf-8")
    result = _run_offline_cli(xml_path, html_path)
    assert result.returncode == 1
    assert result.stdout == "FAIL HTML_MISMATCH\n"
    assert "Traceback" not in result.stdout + result.stderr
    assert not result.stderr


def test_offline_cli_preserves_unsupported_status_and_exit_code(tmp_path: Path) -> None:
    source = (EXAMPLES / f"{EXAMPLE_NAMES[0]}.xml").read_bytes()
    unsupported = source.replace(
        b"<RodzajFaktury>VAT</RodzajFaktury>",
        b"<RodzajFaktury>KOR</RodzajFaktury>",
    )
    xml_path = tmp_path / "unsupported.xml"
    html_path = tmp_path / "page.html"
    xml_path.write_bytes(unsupported)
    html_path.write_text("<html></html>", encoding="utf-8")
    result = _run_offline_cli(xml_path, html_path)
    assert result.returncode == 2
    assert result.stdout == "UNSUPPORTED PROFILE_UNSUPPORTED\n"
    assert not result.stderr


if __name__ == "__main__":
    raise SystemExit(_offline_main())
