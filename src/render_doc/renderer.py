"""Render a supported FA(3) invoice profile as a standalone HTML document.

Features (EN):
- Parses XML without loading DTDs, entities, or network resources.
- Renders a restricted PLN basic invoice profile.
- Renders multiple rows, including exempt sales and supported payment details.

Funkcje (PL):
- Parsuje XML bez wczytywania DTD, encji ani zasobów sieciowych.
- Renderuje ograniczony profil faktury PLN, w tym sprzedaż zwolnioną i obsługiwane dane płatności.

File: src/render_doc/renderer.py
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
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
    "zw": ("zwolniona", "P_13_7", None),
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


def _payment_data(invoice: etree._Element) -> tuple[str, str, str]:
    payments = invoice.findall(_qualified(invoice, "Platnosc"))
    if len(payments) > 1:
        raise UnsupportedDocumentError("Pole Platnosc występuje wielokrotnie.")
    if not payments:
        return "", "", ""

    payment = payments[0]
    _children(payment, {"TerminPlatnosci", "FormaPlatnosci", "RachunekBankowy"})
    field_order = [
        etree.QName(child).localname for child in payment if isinstance(child.tag, str)
    ]
    if field_order not in (
        ["TerminPlatnosci"],
        ["TerminPlatnosci", "FormaPlatnosci"],
        ["TerminPlatnosci", "RachunekBankowy"],
        ["TerminPlatnosci", "FormaPlatnosci", "RachunekBankowy"],
    ):
        raise UnsupportedDocumentError(
            "Obsługiwany jest wyłącznie pojedynczy TerminPlatnosci, "
            "opcjonalnie z FormaPlatnosci i pojedynczym RachunekBankowy w kolejności FA(3)."
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

    payment_form = ""
    if "FormaPlatnosci" in field_order:
        form_code = _text(payment, "FormaPlatnosci")
        try:
            payment_form = _PAYMENT_FORMS[form_code]
        except KeyError as exc:
            raise UnsupportedDocumentError(
                "Nieobsługiwana wartość pola FormaPlatnosci."
            ) from exc

    bank_account = ""
    if "RachunekBankowy" in field_order:
        account = _one(payment, "RachunekBankowy")
        _children(account, {"NrRB"})
        bank_account = _text(account, "NrRB")
    return due_date, payment_form, bank_account


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
    payment_due_date, payment_form, bank_account = _payment_data(invoice)
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
        "bank_account": bank_account,
    }
    return data, rows, summary, additional_descriptions


def _e(value: str) -> str:
    return escape(value, quote=True)


def _format_pl_number(value: str) -> str:
    """Format a validated source decimal for Polish display without rounding."""
    number = Decimal(value)
    precision = max(0, -number.as_tuple().exponent)
    formatted = f"{number:,.{precision}f}"
    return formatted.replace(",", "\u00a0").replace(".", ",")


def _party_html(label: str, value: str, address: list[str]) -> str:
    """Render a party identity with name and NIP on separate lines."""
    name, separator, nip = value.rpartition(" (NIP: ")
    if not separator or not nip.endswith(")"):
        name, nip = value, ""
    nip_html = f'<p class="nip">NIP: {_e(nip[:-1])}</p>' if nip else ""
    address_html = "<br>".join(_e(line) for line in address)
    return (
        f"<td><h2>{label}</h2><p class=\"party-name\">{_e(name)}</p>"
        f"{nip_html}<p class=\"address\">{address_html}</p></td>"
    )


def _render_classic_html(
    data: dict[str, object],
    rows: list[dict[str, str]],
    summary: list[dict[str, str | None]],
    additional_descriptions: list[dict[str, str]],
    ksef_number: str | None,
) -> str:
    """Render parsed invoice data with the compact accounting layout."""
    line_html = "\n".join(
        "<tr>"
        f"<td class=\"number\">{_e(row['number'])}</td>"
        f"<td>{_e(row['description'])}</td>"
        f"<td class=\"number\">{_e(_format_pl_number(row['quantity']))} {_e(row['unit']) if row['unit'] else '—'}</td>"
        f"<td class=\"number\">{_e(_format_pl_number(row['unit_net']))} {_e(data['currency'])}</td>"
        f"<td class=\"number\">{_e(row['tax_rate'])}</td>"
        f"<td class=\"number\">{_e(_format_pl_number(row['net']))} {_e(data['currency'])}</td>"
        "</tr>"
        for row in rows
    )
    summary_html = "\n".join(
        "<tr>"
        f"<td>{_e(item['rate'] or '')}</td><td class=\"number\">{_e(_format_pl_number(item['net'] or '0'))} {_e(data['currency'])}</td>"
        f"<td class=\"number\">{_e(_format_pl_number(item['vat'])) + ' ' + _e(data['currency']) if item['vat'] is not None else '—'}</td>"
        "</tr>"
        for item in summary
    )
    parties = "\n".join(
        _party_html(label, data[key], data[address_key])
        for label, key, address_key in (
            ("Sprzedawca", "seller", "seller_address"),
            ("Nabywca", "buyer", "buyer_address"),
        )
    )
    payment_fields = []
    for label, key in (
        ("Termin płatności", "payment_due_date"),
        ("Forma płatności", "payment_form"),
        ("Rachunek bankowy", "bank_account"),
    ):
        if data[key]:
            payment_fields.append(
                f"<tr><th>{label}</th><td>{_e(data[key])}</td></tr>"
            )
    payment_html = (
        "<section><h2>Płatność</h2><table class=\"details\">"
        + "".join(payment_fields)
        + "</table></section>"
        if payment_fields
        else ""
    )
    delivery = (
        f"<tr><th>Data dostawy lub wykonania usługi</th><td>{_e(data['delivery_date'])}</td></tr>"
        if data["delivery_date"]
        else ""
    )
    ksef = (
        f"<p class=\"ksef\"><strong>Numer KSeF:</strong> {_e(ksef_number)}</p>"
        if ksef_number is not None
        else ""
    )
    descriptions = "".join(
        f"<tr><th>{_e(item['key'])}</th><td>{_e(item['value'])}</td></tr>"
        for item in additional_descriptions
    )
    extra = (
        f"<section><h2>Dodatkowe informacje</h2><table class=\"details\">{descriptions}</table></section>"
        if descriptions
        else ""
    )
    return f"""<!doctype html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Faktura {_e(data['number'])}</title><style>
* {{ box-sizing: border-box; }} body {{ margin: 10px auto; padding: 0 10px; max-width: 650px; color: #202020; background: #fff; font: 14px Arial, Helvetica, sans-serif; line-height: 1.3; }}
h1 {{ margin: 0; font-size: 20px; }} h2 {{ margin: 0 0 5px; font-size: 14px; }} p {{ margin: 3px 0; overflow-wrap: anywhere; }} section {{ margin: 8px 0; padding: 5px 0; }}
.meta, .parties, .items, .vat, .details {{ width: 100%; border-collapse: collapse; table-layout: fixed; }} .meta th, .meta td, .parties td, .items th, .items td, .vat th, .vat td, .details th, .details td {{ border-bottom: 1px solid #c7c7c7; padding: 4px 5px; vertical-align: top; overflow-wrap: anywhere; }}
.meta th, .details th {{ width: 43%; text-align: left; font-weight: normal; }} .parties {{ margin: 7px 0; }} .parties td {{ width: 50%; border-bottom: 1px solid #aaa; }} .nip, .address {{ color: #444; font-size: 12px; }} .items {{ font-size: 11px; }} .items th {{ text-align: left; border-top: 1px solid #777; background: #f4f4f4; }} .items th:nth-child(1) {{ width: 7%; }} .items th:nth-child(2) {{ width: 31%; }} .items th:nth-child(3) {{ width: 14%; }} .items th:nth-child(4) {{ width: 17%; }} .items th:nth-child(5) {{ width: 11%; }} .items th:nth-child(6) {{ width: 20%; }}
.number {{ text-align: right; font-variant-numeric: tabular-nums; }} .vat th {{ border-top: 1px solid #777; text-align: left; background: #f4f4f4; }} .due {{ margin: 7px 0; padding: 7px 0; border-top: 2px solid #444; border-bottom: 2px solid #444; text-align: right; font-size: 17px; overflow-wrap: anywhere; }} .ksef {{ margin: 5px 0; font-size: 12px; overflow-wrap: anywhere; word-break: break-word; }}
@page {{ size: A4; margin: 12mm; }} @media print {{ body {{ max-width: none; margin: 0; padding: 0; font-size: 10pt; }} section {{ break-inside: avoid; }} }}
</style></head><body><h1>Faktura {_e(data['number'])}</h1>
<table class="meta"><tr><th>Data wystawienia</th><td>{_e(data['issue_date'])}</td></tr>{delivery}</table>{ksef}
<table class="parties"><tr>{parties}</tr></table>{payment_html}
<section><h2>Pozycje faktury</h2><table class="items"><thead><tr><th>Nr</th><th>Opis</th><th>Ilość / jedn.</th><th>Cena netto</th><th>VAT</th><th>Wartość netto</th></tr></thead><tbody>{line_html}</tbody></table></section>
<section><h2>Podsumowanie VAT</h2><table class="vat"><thead><tr><th>Stawka</th><th class="number">Netto</th><th class="number">VAT</th></tr></thead><tbody>{summary_html}</tbody></table></section>
<p class="due"><strong>Do zapłaty: {_e(_format_pl_number(data['gross']))} {_e(data['currency'])}</strong></p>{extra}</body></html>
"""


def render_fa3_html(
    xml_bytes: bytes,
    *,
    ksef_number: str | None = None,
    template: str = "default",
) -> str:
    """Render a supported FA(3) XML invoice profile as HTML."""
    if ksef_number is not None and not isinstance(ksef_number, str):
        raise TypeError("ksef_number must be str or None")
    if template not in ("default", "classic"):
        raise ValueError("template must be 'default' or 'classic'")

    data, rows, summary, additional_descriptions = _parse_invoice(xml_bytes)
    if template == "classic":
        return _render_classic_html(data, rows, summary, additional_descriptions, ksef_number)
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
        + (
            f"<br><strong>Rachunek bankowy:</strong> {_e(data['bank_account'])}"
            if data["bank_account"]
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
