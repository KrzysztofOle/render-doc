"""Render a supported FA(3) invoice profile as a standalone HTML document.

Features (EN):
- Parses XML without loading DTDs, entities, or network resources.
- Renders a restricted PLN, 23% VAT basic invoice profile.

Funkcje (PL):
- Parsuje XML bez wczytywania DTD, encji ani zasobów sieciowych.
- Renderuje ograniczony profil podstawowej faktury PLN ze stawką VAT 23%.

File: src/render_doc/renderer.py
"""

from __future__ import annotations

from datetime import date
from html import escape
from io import BytesIO
import re

from lxml import etree


class RenderDocError(ValueError):
    """Błąd danych wejściowych renderera."""


class InvalidXmlError(RenderDocError):
    """Nie można bezpiecznie odczytać wejściowego XML."""


class UnsupportedDocumentError(RenderDocError):
    """Dokument nie należy do obsługiwanego profilu FA(3)."""


def _qualified(parent: etree._Element, name: str) -> str:
    namespace = etree.QName(parent).namespace
    return f"{{{namespace}}}{name}" if namespace else name


def _one(parent: etree._Element, name: str) -> etree._Element:
    found = parent.findall(_qualified(parent, name))
    if len(found) != 1:
        raise UnsupportedDocumentError(f"Wymagany jest dokładnie jeden element {name}.")
    return found[0]


def _text(parent: etree._Element, name: str, *, required: bool = True) -> str:
    found = parent.findall(_qualified(parent, name))
    if len(found) > 1:
        raise UnsupportedDocumentError(f"Pole {name} występuje wielokrotnie.")
    if not found:
        if required:
            raise UnsupportedDocumentError(f"Brak wymaganego pola {name}.")
        return ""
    value = found[0].text
    if value is None or not value.strip():
        if required:
            raise UnsupportedDocumentError(f"Pole {name} jest puste.")
        return ""
    return value.strip()


def _children(parent: etree._Element, allowed: set[str]) -> None:
    namespace = etree.QName(parent).namespace
    unexpected = {
        etree.QName(child).localname
        for child in parent
        if isinstance(child.tag, str)
        and (
            etree.QName(child).namespace != namespace
            or etree.QName(child).localname not in allowed
        )
    }
    if unexpected:
        raise UnsupportedDocumentError(
            "Nieobsługiwane pola: " + ", ".join(sorted(unexpected)) + "."
        )


def _decimal(parent: etree._Element, name: str) -> str:
    value = _text(parent, name)
    if not re.fullmatch(r"[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)", value):
        raise UnsupportedDocumentError(
            f"Pole {name} nie ma formatu liczby dziesiętnej FA(3)."
        )
    return value


def _party(root: etree._Element, name: str) -> tuple[str, list[str]]:
    party = _one(root, name)
    _children(party, {"DaneIdentyfikacyjne", "Adres"})
    identity = _one(party, "DaneIdentyfikacyjne")
    _children(identity, {"NIP", "Nazwa"})
    display_name = f"{_text(identity, 'Nazwa')} (NIP: {_text(identity, 'NIP')})"
    addresses = party.findall(_qualified(party, "Adres"))
    if len(addresses) > 1:
        raise UnsupportedDocumentError("Wiele adresów podmiotu nie jest obsługiwanych.")
    address_lines: list[str] = []
    if addresses:
        address = addresses[0]
        _children(address, {"KodKraju", "AdresL1", "AdresL2"})
        country = _text(address, "KodKraju", required=False)
        if country:
            address_lines.append(country)
        for field in ("AdresL1", "AdresL2"):
            value = _text(address, field, required=False)
            if value:
                address_lines.append(value)
    return display_name, address_lines


def _parse_invoice(xml_bytes: bytes) -> tuple[dict[str, object], list[dict[str, str]]]:
    if not isinstance(xml_bytes, bytes):
        raise TypeError("xml_bytes musi mieć typ bytes.")
    parser = etree.XMLParser(
        resolve_entities=False,
        load_dtd=False,
        no_network=True,
        recover=False,
        huge_tree=False,
    )
    try:
        tree = etree.parse(BytesIO(xml_bytes), parser)
    except (etree.XMLSyntaxError, ValueError) as exc:
        raise InvalidXmlError("Nie można odczytać dokumentu XML.") from exc
    if tree.docinfo.doctype:
        raise InvalidXmlError("Dokumenty XML z deklaracją DTD nie są obsługiwane.")

    root = tree.getroot()
    if (
        etree.QName(root).localname != "Faktura"
        or etree.QName(root).namespace != "http://crd.gov.pl/wzor/2025/06/25/13775/"
    ):
        raise UnsupportedDocumentError(
            "Oczekiwano dokumentu FA(3) z elementem Faktura."
        )
    _children(root, {"Naglowek", "Podmiot1", "Podmiot2", "Fa"})
    header = _one(root, "Naglowek")
    _children(
        header,
        {"KodFormularza", "WariantFormularza", "DataWytworzeniaFa", "SystemInfo"},
    )
    code = _one(header, "KodFormularza")
    if code.get("kodSystemowy") != "FA (3)" or code.get("wersjaSchemy") != "1-0E":
        raise UnsupportedDocumentError(
            "Obsługiwana jest wyłącznie struktura FA(3), wersja 1-0E."
        )
    if (code.text or "").strip() != "FA":
        raise UnsupportedDocumentError("Nieobsługiwana wartość KodFormularza.")
    if _text(header, "WariantFormularza") != "3":
        raise UnsupportedDocumentError("Nieobsługiwany wariant formularza.")
    _text(header, "DataWytworzeniaFa")

    seller, seller_address = _party(root, "Podmiot1")
    buyer, buyer_address = _party(root, "Podmiot2")
    invoice = _one(root, "Fa")
    allowed_invoice_fields = {
        "KodWaluty",
        "P_1",
        "P_2",
        "P_13_1",
        "P_14_1",
        "P_15",
        "FaWiersz",
        "RodzajFaktury",
    }
    _children(invoice, allowed_invoice_fields)
    if _text(invoice, "RodzajFaktury") != "VAT":
        raise UnsupportedDocumentError(
            "Obsługiwana jest wyłącznie podstawowa faktura VAT."
        )
    currency = _text(invoice, "KodWaluty")
    if currency != "PLN":
        raise UnsupportedDocumentError("Obsługiwana jest wyłącznie waluta PLN.")

    rows: list[dict[str, str]] = []
    for row in invoice.findall(_qualified(invoice, "FaWiersz")):
        _children(row, {"NrWierszaFa", "P_7", "P_8A", "P_8B", "P_9A", "P_11", "P_12"})
        if _text(row, "P_12") != "23":
            raise UnsupportedDocumentError("Obsługiwana jest wyłącznie stawka VAT 23%.")
        rows.append(
            {
                "description": _text(row, "P_7"),
                "unit": _text(row, "P_8A", required=False),
                "quantity": _decimal(row, "P_8B"),
                "unit_net": _decimal(row, "P_9A"),
                "net": _decimal(row, "P_11"),
                "tax_rate": "23%",
            }
        )
    if not rows:
        raise UnsupportedDocumentError(
            "Faktura musi zawierać co najmniej jedną pozycję."
        )

    issue_date = _text(invoice, "P_1")
    try:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", issue_date):
            raise ValueError
        date.fromisoformat(issue_date)
    except ValueError as exc:
        raise UnsupportedDocumentError(
            "Pole P_1 nie zawiera prawidłowej daty FA(3)."
        ) from exc
    data: dict[str, object] = {
        "number": _text(invoice, "P_2"),
        "issue_date": issue_date,
        "seller": seller,
        "seller_address": seller_address,
        "buyer": buyer,
        "buyer_address": buyer_address,
        "net": _decimal(invoice, "P_13_1"),
        "vat": _decimal(invoice, "P_14_1"),
        "gross": _decimal(invoice, "P_15"),
        "currency": currency,
    }
    return data, rows


def _e(value: str) -> str:
    return escape(value, quote=True)


def render_fa3_html(xml_bytes: bytes) -> str:
    """Render an explicitly supported FA(3) XML invoice profile as HTML."""
    data, rows = _parse_invoice(xml_bytes)
    line_html = "\n".join(
        "<tr>"
        f"<td>{_e(row['description'])}</td>"
        f"<td>{_e(row['quantity'])} {_e(row['unit'])}</td>"
        f"<td>{_e(row['unit_net'])} {_e(data['currency'])}</td>"
        f"<td>{_e(row['tax_rate'])}</td>"
        f"<td>{_e(row['net'])} {_e(data['currency'])}</td>"
        "</tr>"
        for row in rows
    )
    seller_address = "<br>".join(_e(value) for value in data["seller_address"])
    buyer_address = "<br>".join(_e(value) for value in data["buyer_address"])
    return f"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Faktura {_e(data["number"])}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #20252b; margin: 2rem auto; max-width: 960px; padding: 0 1rem; }}
h1, h2 {{ color: #17324d; }}
.parties {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin: 2rem 0; }}
section {{ border: 1px solid #ccd4dc; border-radius: .35rem; padding: 1rem; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border-bottom: 1px solid #ccd4dc; padding: .65rem; text-align: left; }}
th {{ background: #eef2f5; }}
.summary {{ margin: 1.5rem 0 0 auto; max-width: 24rem; }}
.summary div {{ display: flex; justify-content: space-between; padding: .35rem 0; }}
@media print {{ body {{ margin: 0; max-width: none; }} }}
@media (max-width: 600px) {{ .parties {{ grid-template-columns: 1fr; }} table {{ font-size: .85rem; }} th, td {{ padding: .4rem; }} }}
</style>
</head>
<body>
<header><h1>Faktura</h1><p><strong>Numer:</strong> {_e(data["number"])}<br><strong>Data wystawienia:</strong> {_e(data["issue_date"])}</p></header>
<div class="parties">
<section><h2>Sprzedawca</h2><p>{_e(data["seller"])}<br>{seller_address}</p></section>
<section><h2>Nabywca</h2><p>{_e(data["buyer"])}<br>{buyer_address}</p></section>
</div>
<section><h2>Pozycje faktury</h2><table><thead><tr><th>Opis</th><th>Ilość i jednostka</th><th>Cena netto</th><th>VAT</th><th>Wartość netto</th></tr></thead><tbody>{line_html}</tbody></table></section>
<section class="summary" aria-label="Podsumowanie faktury"><h2>Podsumowanie</h2><div><span>Netto</span><strong>{_e(data["net"])} {_e(data["currency"])}</strong></div><div><span>VAT</span><strong>{_e(data["vat"])} {_e(data["currency"])}</strong></div><div><span>Należność ogółem (brutto)</span><strong>{_e(data["gross"])} {_e(data["currency"])}</strong></div></section>
</body>
</html>
"""
