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

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
import re
from xml.etree import ElementTree

import pytest

from render_doc import UnsupportedDocumentError, render_fa3_html


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

    _VOID = {
        "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("#document", {})
        self.stack = [self.root]

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
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


def _parse_html(html: str) -> _Node:
    parser = _DocumentParser()
    parser.feed(html)
    parser.close()
    return parser.root


def _class_nodes(root: _Node, class_name: str) -> list[_Node]:
    return [
        node for node in root.descendants()
        if class_name in (node.attrs.get("class") or "").split()
    ]


def _source_text(parent: ElementTree.Element, path: str, *, required: bool = True) -> str:
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
    cards = [node for node in _class_nodes(root, "party-card") if node.first("h2").text == label]
    assert len(cards) == 1
    card = cards[0]
    assert _class_nodes(card, "party-name")[0].text == _source_text(identity, "fa:Nazwa")
    assert _class_nodes(card, "party-nip")[0].text == f"NIP: {_source_text(identity, 'fa:NIP')}"
    addresses = party.findall("fa:Adres", NS)
    expected_address = []
    for address in addresses:
        for field_name in ("KodKraju", "AdresL1", "AdresL2"):
            value = _source_text(address, f"fa:{field_name}", required=False)
            if value:
                expected_address.append(value)
    assert [node.text for node in _class_nodes(card, "party-address")] == expected_address


def assert_supported_source_matches_ksef_html(xml_bytes: bytes, html: str) -> None:
    """Compare source values independently with their expected HTML sections."""
    source = ElementTree.fromstring(xml_bytes)
    root = _parse_html(html)
    invoice = source.find("fa:Fa", NS)
    assert invoice is not None

    assert _class_nodes(root, "invoice-number")[0].text == _source_text(invoice, "fa:P_2")
    details = _class_nodes(root, "details")
    assert len(details) == 1
    detail_values = {
        child.first("span").text: child.descendants("span")[-1].text
        for child in details[0].descendants("div")
        if len(child.descendants("span")) >= 2
    }
    assert detail_values["Data wystawienia"] == _pl_date(_source_text(invoice, "fa:P_1"))
    assert detail_values["Waluta"] == _source_text(invoice, "fa:KodWaluty")
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

    summaries: list[tuple[str, str, str]] = []
    seen_rates = {_source_text(row, "fa:P_12") for row in source_rows}
    for source_rate, (label, net_field, tax_field) in VAT_RATES.items():
        net = _source_text(invoice, f"fa:{net_field}", required=False)
        if not net:
            assert source_rate not in seen_rates
            continue
        tax = _source_text(invoice, f"fa:{tax_field}", required=False) if tax_field else ""
        summaries.append((label, _pl_number(net), _pl_number(tax) if tax else "—"))
    summary_tables = _class_nodes(root, "vat-summary")
    assert len(summary_tables) == 1
    summary_rows = [row for row in summary_tables[0].descendants("tr") if row.descendants("td")]
    assert len(summary_rows) == len(summaries)
    for row, expected in zip(summary_rows, summaries, strict=True):
        cells = row.descendants("td")
        assert tuple(cell.text for cell in cells[:3]) == expected

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
            payment_expected.append(("Forma płatności", PAYMENT_FORMS[form.text.strip()]))
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


@pytest.mark.parametrize("name", EXAMPLE_NAMES)
def test_ksef_html_preserves_accounting_fields_by_source_section(name: str) -> None:
    xml_bytes = (EXAMPLES / f"{name}.xml").read_bytes()
    html = render_fa3_html(xml_bytes, template="ksef")
    assert_supported_source_matches_ksef_html(xml_bytes, html)


def _assert_mutation_rejected(xml_bytes: bytes, html: str, original: str, changed: str) -> None:
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
    row = re.search(r"<tr>(?:(?!</tr>).)*Wdrozenie systemu etap pierwszy(?:(?!</tr>).)*</tr>", html)
    assert row is not None
    with pytest.raises(AssertionError):
        assert_supported_source_matches_ksef_html(xml_bytes, html.replace(row.group(0), "", 1))


def test_detects_substituted_invoice_row_amount() -> None:
    xml_bytes = (EXAMPLES / f"{EXAMPLE_NAMES[2]}.xml").read_bytes()
    html = render_fa3_html(xml_bytes, template="ksef")
    row = re.search(r"<tr>(?:(?!</tr>).)*Wdrozenie systemu etap pierwszy(?:(?!</tr>).)*</tr>", html)
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
        assert_supported_source_matches_ksef_html(xml_bytes, html.replace(account, "", 1))


def test_detects_data_assigned_to_wrong_party_section() -> None:
    xml_bytes = (EXAMPLES / f"{EXAMPLE_NAMES[0]}.xml").read_bytes()
    html = render_fa3_html(xml_bytes, template="ksef")
    _assert_mutation_rejected(xml_bytes, html, "0000000000", "0000000001")


def test_rejects_unsupported_invoice_type_instead_of_partial_render() -> None:
    xml_bytes = (EXAMPLES / f"{EXAMPLE_NAMES[0]}.xml").read_bytes()
    unsupported = xml_bytes.replace(
        b"<RodzajFaktury>VAT</RodzajFaktury>",
        b"<RodzajFaktury>KOR</RodzajFaktury>",
    )
    with pytest.raises(UnsupportedDocumentError):
        render_fa3_html(unsupported, template="ksef")
