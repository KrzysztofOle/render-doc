"""Render a supported FA(3) invoice profile as a standalone HTML document.

Features (EN):
- Parses XML without loading DTDs, entities, or network resources.
- Renders a restricted PLN, 23% VAT basic invoice profile.
- Renders multiple rows with 23%, 8%, 5%, and explicit 0% variants.

Funkcje (PL):
- Parsuje XML bez wczytywania DTD, encji ani zasobów sieciowych.
- Renderuje ograniczony profil faktury PLN ze stawkami 23%, 8%, 5% i wariantami 0%.

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


def _fa3_date(parent: etree._Element, name: str) -> str:
    value = _text(parent, name)
    try:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError
        date.fromisoformat(value)
    except ValueError as exc:
        raise UnsupportedDocumentError(
            f"Pole {name} nie zawiera prawidłowej daty FA(3)."
        ) from exc
    return value


def _validate_annotations(invoice: etree._Element) -> None:
    annotations = invoice.findall(_qualified(invoice, "Adnotacje"))
    if len(annotations) > 1:
        raise UnsupportedDocumentError("Pole Adnotacje występuje wielokrotnie.")
    if not annotations:
        return
    node = annotations[0]
    _children(
        node,
        {
            "P_16",
            "P_17",
            "P_18",
            "P_18A",
            "Zwolnienie",
            "NoweSrodkiTransportu",
            "P_23",
            "PMarzy",
        },
    )
    for field in ("P_16", "P_17", "P_18", "P_18A", "P_23"):
        if _text(node, field) != "2":
            raise UnsupportedDocumentError(
                f"Obsługiwana jest wyłącznie nieaktywna wartość 2 w polu {field}."
            )
    for group, marker in (
        ("Zwolnienie", "P_19N"),
        ("NoweSrodkiTransportu", "P_22N"),
        ("PMarzy", "P_PMarzyN"),
    ):
        child = _one(node, group)
        _children(child, {marker})
        if _text(child, marker) != "1":
            raise UnsupportedDocumentError(
                f"Obsługiwany jest wyłącznie znacznik braku {marker}=1."
            )


def _additional_descriptions(
    invoice: etree._Element,
) -> list[dict[str, str]]:
    descriptions: list[dict[str, str]] = []
    for description in invoice.findall(_qualified(invoice, "DodatkowyOpis")):
        _children(description, {"Klucz", "Wartosc"})
        descriptions.append(
            {"key": _text(description, "Klucz"), "value": _text(description, "Wartosc")}
        )
    return descriptions


_VAT_RATES = {
    "23": ("23%", "P_13_1", "P_14_1"),
    "8": ("8%", "P_13_2", "P_14_2"),
    "5": ("5%", "P_13_3", "P_14_3"),
    "0 KR": ("0% (krajowa)", "P_13_6_1", None),
    "0 WDT": ("0% (WDT)", "P_13_6_2", None),
    "0 EX": ("0% (eksport)", "P_13_6_3", None),
}

_PAYMENT_FORMS = {
    "1": "Gotówka",
    "2": "Karta",
    "3": "Bon",
    "4": "Czek",
    "5": "Kredyt",
    "6": "Przelew",
    "7": "Płatność mobilna",
}


def _payment_data(invoice: etree._Element) -> tuple[str, str]:
    payments = invoice.findall(_qualified(invoice, "Platnosc"))
    if len(payments) > 1:
        raise UnsupportedDocumentError("Pole Platnosc występuje wielokrotnie.")
    if not payments:
        return "", ""

    payment = payments[0]
    _children(payment, {"TerminPlatnosci", "FormaPlatnosci"})
    field_order = [
        etree.QName(child).localname for child in payment if isinstance(child.tag, str)
    ]
    if field_order not in (
        ["TerminPlatnosci"],
        ["TerminPlatnosci", "FormaPlatnosci"],
    ):
        raise UnsupportedDocumentError(
            "Obsługiwany jest wyłącznie pojedynczy TerminPlatnosci, "
            "opcjonalnie z następującą po nim FormaPlatnosci."
        )

    term = _one(payment, "TerminPlatnosci")
    _children(term, {"Termin"})
    term_fields = [
        etree.QName(child).localname for child in term if isinstance(child.tag, str)
    ]
    if term_fields != ["Termin"]:
        raise UnsupportedDocumentError(
            "Obsługiwany TerminPlatnosci zawiera wyłącznie jedno pole Termin."
        )
    due_date = _fa3_date(term, "Termin")

    if len(field_order) == 1:
        return due_date, ""
    form_code = _text(payment, "FormaPlatnosci")
    try:
        payment_form = _PAYMENT_FORMS[form_code]
    except KeyError as exc:
        raise UnsupportedDocumentError(
            "Nieobsługiwana wartość pola FormaPlatnosci."
        ) from exc
    return due_date, payment_form


def _party(
    root: etree._Element, name: str, *, buyer: bool = False
) -> tuple[str, list[str]]:
    party = _one(root, name)
    allowed_fields = {"DaneIdentyfikacyjne", "Adres"}
    if buyer:
        allowed_fields.update({"JST", "GV"})
    _children(party, allowed_fields)
    if buyer:
        for field in ("JST", "GV"):
            if _text(party, field) != "2":
                raise UnsupportedDocumentError(
                    f"Obsługiwana jest wyłącznie wartość 2 w polu {field}."
                )
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


def _parse_invoice(
    xml_bytes: bytes,
) -> tuple[
    dict[str, object],
    list[dict[str, str]],
    list[dict[str, str | None]],
    list[dict[str, str]],
]:
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
    buyer, buyer_address = _party(root, "Podmiot2", buyer=True)
    invoice = _one(root, "Fa")
    allowed_invoice_fields = {
        "KodWaluty",
        "P_1",
        "P_6",
        "P_2",
        *(field for rate in _VAT_RATES.values() for field in rate[1:] if field),
        "P_15",
        "FaWiersz",
        "RodzajFaktury",
        "Adnotacje",
        "DodatkowyOpis",
        "Platnosc",
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
    observed_rates: set[str] = set()
    for row in invoice.findall(_qualified(invoice, "FaWiersz")):
        _children(row, {"NrWierszaFa", "P_7", "P_8A", "P_8B", "P_9A", "P_11", "P_12"})
        source_rate = _text(row, "P_12")
        if source_rate not in _VAT_RATES:
            raise UnsupportedDocumentError(
                f"Nieobsługiwana stawka VAT w polu P_12: {source_rate}."
            )
        observed_rates.add(source_rate)
        rows.append(
            {
                "number": _text(row, "NrWierszaFa"),
                "description": _text(row, "P_7"),
                "unit": _text(row, "P_8A", required=False),
                "quantity": _decimal(row, "P_8B"),
                "unit_net": _decimal(row, "P_9A"),
                "net": _decimal(row, "P_11"),
                "tax_rate": _VAT_RATES[source_rate][0],
            }
        )
    if not rows:
        raise UnsupportedDocumentError(
            "Faktura musi zawierać co najmniej jedną pozycję."
        )

    issue_date = _fa3_date(invoice, "P_1")
    delivery_date = (
        _fa3_date(invoice, "P_6") if invoice.findall(_qualified(invoice, "P_6")) else ""
    )
    _validate_annotations(invoice)
    additional_descriptions = _additional_descriptions(invoice)
    payment_due_date, payment_form = _payment_data(invoice)
    summary: list[dict[str, str | None]] = []
    for code, (label, net_field, tax_field) in _VAT_RATES.items():
        has_net = bool(invoice.findall(_qualified(invoice, net_field)))
        has_tax = bool(tax_field and invoice.findall(_qualified(invoice, tax_field)))
        if (has_net != has_tax) and tax_field:
            raise UnsupportedDocumentError(
                f"Niepełne podsumowanie VAT dla stawki {label}: wymagane pola "
                f"{net_field} i {tax_field}."
            )
        if code in observed_rates and not has_net:
            required = f"{net_field} i {tax_field}" if tax_field else net_field
            raise UnsupportedDocumentError(
                f"Brak wymaganych pól sumarycznych dla stawki {label}: {required}."
            )
        if has_net:
            summary.append(
                {
                    "rate": label,
                    "net": _decimal(invoice, net_field),
                    "vat": _decimal(invoice, tax_field)
                    if tax_field and has_tax
                    else None,
                }
            )
    data: dict[str, object] = {
        "number": _text(invoice, "P_2"),
        "issue_date": issue_date,
        "delivery_date": delivery_date,
        "seller": seller,
        "seller_address": seller_address,
        "buyer": buyer,
        "buyer_address": buyer_address,
        "gross": _decimal(invoice, "P_15"),
        "currency": currency,
        "payment_due_date": payment_due_date,
        "payment_form": payment_form,
    }
    return data, rows, summary, additional_descriptions


def _e(value: str) -> str:
    return escape(value, quote=True)


def render_fa3_html(
    xml_bytes: bytes,
    *,
    ksef_number: str | None = None,
) -> str:
    """Render a supported FA(3) XML invoice profile as HTML."""
    if ksef_number is not None and not isinstance(ksef_number, str):
        raise TypeError("ksef_number must be str or None")

    data, rows, summary, additional_descriptions = _parse_invoice(xml_bytes)
    line_html = "\n".join(
        "<tr>"
        f"<td>{_e(row['number'])}</td>"
        f"<td>{_e(row['description'])}</td>"
        f"<td>{_e(row['quantity'])} {_e(row['unit']) if row['unit'] else '—'}</td>"
        f"<td>{_e(row['unit_net'])} {_e(data['currency'])}</td>"
        f"<td>{_e(row['tax_rate'])}</td>"
        f"<td>{_e(row['net'])} {_e(data['currency'])}</td>"
        "</tr>"
        for row in rows
    )
    summary_html = "\n".join(
        "<div>"
        f"<span>Netto {_e(item['rate'] or '')}</span>"
        f"<strong>{_e(item['net'] or '')} {_e(data['currency'])}</strong>"
        "</div>"
        + (
            "<div>"
            f"<span>VAT {_e(item['rate'] or '')}</span>"
            f"<strong>{_e(item['vat'])} {_e(data['currency'])}</strong>"
            "</div>"
            if item["vat"] is not None
            else ""
        )
        for item in summary
    )
    seller_address = "<br>".join(_e(value) for value in data["seller_address"])
    buyer_address = "<br>".join(_e(value) for value in data["buyer_address"])
    descriptions_html = "\n".join(
        f"<dt>{_e(item['key'])}</dt><dd>{_e(item['value'])}</dd>"
        for item in additional_descriptions
    )
    delivery_date_html = (
        f"<br><strong>Data dostawy lub wykonania usługi:</strong> "
        f"{_e(data['delivery_date'])}"
        if data["delivery_date"]
        else ""
    )
    ksef_number_html = (
        "\n<section><h2>Identyfikacja KSeF</h2><p><strong>Numer KSeF:</strong> "
        f"{_e(ksef_number)}</p></section>"
        if ksef_number is not None
        else ""
    )
    payment_html = (
        "\n<section><h2>Płatność</h2><p>"
        f"<strong>Termin płatności:</strong> {_e(data['payment_due_date'])}"
        + (
            f"<br><strong>Forma płatności:</strong> {_e(data['payment_form'])}"
            if data["payment_form"]
            else ""
        )
        + "</p></section>"
        if data["payment_due_date"]
        else ""
    )
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
<header><h1>Faktura</h1><p><strong>Numer:</strong> {_e(data["number"])}<br><strong>Data wystawienia:</strong> {_e(data["issue_date"])}{delivery_date_html}</p></header>{ksef_number_html}{payment_html}
<div class="parties">
<section><h2>Sprzedawca</h2><p>{_e(data["seller"])}<br>{seller_address}</p></section>
<section><h2>Nabywca</h2><p>{_e(data["buyer"])}<br>{buyer_address}</p></section>
</div>
<section><h2>Pozycje faktury</h2><table><thead><tr><th>Nr wiersza</th><th>Opis</th><th>Ilość i jednostka</th><th>Cena netto</th><th>VAT</th><th>Wartość netto</th></tr></thead><tbody>{line_html}</tbody></table></section>
{"<section><h2>Dodatkowe informacje</h2><dl>" + descriptions_html + "</dl></section>" if descriptions_html else ""}
<section class="summary" aria-label="Podsumowanie faktury"><h2>Podsumowanie</h2>{summary_html}<div><span>Kwota należności ogółem</span><strong>{_e(data["gross"])} {_e(data["currency"])}</strong></div></section>
</body>
</html>
"""
