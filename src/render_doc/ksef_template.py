"""Render a KSeF-inspired, printable FA(3) HTML view.

Features (EN):
- Presents the existing validated FA(3) data model in a standalone A4 layout.
- Keeps QR generation and official-verification links outside the R1 scope.

Funkcje (PL):
- Prezentuje istniejący, zwalidowany model FA(3) w samodzielnym układzie A4.
- Nie generuje kodów QR ani linków weryfikacyjnych na etapie R1.

File: src/render_doc/ksef_template.py
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from html import escape


def _e(value: object) -> str:
    """Escape untrusted text from XML and caller-provided metadata."""
    return escape(str(value), quote=True)


def _pl_decimal(value: str) -> str:
    """Format an original decimal without rounding or discarding precision."""
    number = Decimal(value)
    precision = max(0, -number.as_tuple().exponent)
    text = f"{number:,.{precision}f}"
    return text.replace(",", "\u00a0").replace(".", ",")


def _pl_date(value: object) -> str:
    """Format parser-validated ISO dates for human-readable Polish output."""
    if not value:
        return ""
    return date.fromisoformat(str(value)).strftime("%d.%m.%Y")


def _identity(value: object) -> tuple[str, str]:
    """Split the existing renderer's validated name/NIP presentation value."""
    name, sep, suffix = str(value).rpartition(" (NIP: ")
    if sep and suffix.endswith(")"):
        return name, suffix[:-1]
    return str(value), ""


def _party_card(heading: str, identity: object, address: object) -> str:
    name, nip = _identity(identity)
    lines = "".join(f"<p class=\"party-address\">{_e(line)}</p>" for line in address)
    return (
        '<div class="party-card">'
        f"<h2>{_e(heading)}</h2>"
        f'<p class="party-name">{_e(name)}</p>'
        + (f'<p class="party-nip"><strong>NIP:</strong> {_e(nip)}</p>' if nip else "")
        + lines
        + "</div>"
    )


def _gross_by_rate(entry: dict[str, str | None]) -> str:
    """Provide informative tax-band gross from source net/VAT, not from rows."""
    net = entry["net"]
    tax = entry["vat"]
    if net is None:
        return "—"
    if tax is None:
        # The restricted parser accepts missing tax only for 0% or exempt sales.
        return _pl_decimal(net) if entry["rate"] in ("0 KR", "0 WDT", "0 EX", "zw") else "—"
    precision = max(
        0,
        -Decimal(net).as_tuple().exponent,
        -Decimal(tax).as_tuple().exponent,
    )
    return _pl_decimal(f"{Decimal(net) + Decimal(tax):.{precision}f}")


_CSS = """
* { box-sizing: border-box; }
html { background: #fff; }
body { margin: 0 auto; padding: 24px 28px 18px; max-width: 900px;
       color: #343a40; font: 12px/1.42 Arial, Helvetica, sans-serif; }
h1, h2, h3, p { margin-top: 0; }
h1 { font-size: 24px; line-height: 1.1; margin-bottom: 3px; color: #343a40; }
h2 { font-size: 13px; margin-bottom: 9px; }
h3 { font-size: 12px; margin: 0 0 7px; }
.ksef-brand { display: flex; flex-direction: column; justify-content: flex-start; }
.ksef-word { font-size: 25px; font-weight: 700; letter-spacing: -.04em; }
.ksef-red { color: #c51a29; }
.ksef-subtitle { font-size: 9px; color: #657078; }
.document-header { display: flex; justify-content: space-between; gap: 25px;
                   align-items: flex-start; border-bottom: 2px solid #343a40;
                   padding-bottom: 14px; margin-bottom: 15px; }
.invoice-meta { max-width: 70%; text-align: right; overflow-wrap: anywhere; }
.invoice-meta .label { display: block; font-size: 9px; color: #687078; }
.invoice-number { font-size: 17px; font-weight: 700; line-height: 1.2; overflow-wrap: anywhere; }
.invoice-type { font-size: 11px; font-weight: 700; }
.ksef-number { font-size: 10px; margin-top: 5px; overflow-wrap: anywhere; }
.ksef-number strong { color: #343a40; }
.section { margin: 12px 0 15px; }
.section-title { border-top: 1px solid #afb6bc; padding-top: 9px; margin: 0 0 9px;
                 font-size: 12px; font-weight: 700; }
.parties { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 20px; }
.party-card { min-width: 0; overflow-wrap: anywhere; }
.party-card h2 { font-size: 11px; color: #343a40; }
.party-card p { margin: 0 0 3px; }
.party-name { font-weight: 700; }
.party-nip, .party-address { font-size: 10px; }
.details { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 20px; }
.detail-label { display: block; color: #657078; font-size: 10px; }
.detail-value { display: block; font-weight: 700; }
.table-wrap { width: 100%; }
table { width: 100%; border-collapse: collapse; border-spacing: 0; table-layout: fixed; }
th, td { border: 1px solid #c3c7cc; padding: 6px 5px; vertical-align: top;
         overflow-wrap: anywhere; }
th { background: #f6f7fa; text-align: left; font-size: 10px; font-weight: 700; }
td { font-size: 10px; }
.number { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.description { white-space: pre-wrap; }
.line-index { text-align: center; }
.items .col-nr { width: 6%; }
.items .col-name { width: 32%; }
.items .col-quantity { width: 10%; }
.items .col-unit { width: 9%; }
.items .col-price { width: 16%; }
.items .col-vat { width: 9%; }
.items .col-net { width: 18%; }
.vat-summary { margin-top: 13px; }
.vat-summary .col-rate { width: 25%; }
.vat-summary .col-net, .vat-summary .col-vat, .vat-summary .col-gross { width: 25%; }
.amount-due { display: flex; justify-content: flex-end; align-items: baseline;
              gap: 12px; margin: 13px 0 7px; font-size: 12px; }
.amount-due strong { font-size: 17px; white-space: nowrap; color: #202830; }
.payments td:first-child, .extra td:first-child { width: 35%; font-weight: 700; }
.paper-footer { border-top: 1px solid #afb6bc; padding-top: 6px;
                color: #657078; font-size: 9px; margin-top: 20px; }
@page { size: A4; margin: 12mm;
        @bottom-right { content: counter(page) " / " counter(pages); color: #657078;
                        font: 9pt Arial, Helvetica, sans-serif; } }
@media print {
  html, body { width: auto; max-width: none; margin: 0; padding: 0; }
  thead { display: table-header-group; }
  tr { break-inside: avoid; page-break-inside: avoid; }
  .document-header, .parties, .details, .amount-due, .paper-footer {
    break-inside: avoid; page-break-inside: avoid; }
  .section { margin-top: 10px; }
}
@media screen and (max-width: 640px) {
  body { padding: 15px; }
  .document-header { gap: 10px; }
  .invoice-meta { max-width: 60%; }
  .parties, .details { grid-template-columns: 1fr; }
  .table-wrap { overflow-x: auto; }
  .items { min-width: 700px; }
}
""".strip()


def render_ksef_template(
    data: dict[str, object],
    rows: list[dict[str, str]],
    summary: list[dict[str, str | None]],
    additional_descriptions: list[dict[str, str]],
    ksef_number: str | None,
) -> str:
    """Make an offline, KSeF-inspired HTML document from validated FA(3) data."""
    number = _e(data["number"])
    currency = _e(data["currency"])
    ksef_line = (
        f'<p class="ksef-number"><strong>Numer KSeF:</strong> {_e(ksef_number)}</p>'
        if ksef_number is not None
        else ""
    )
    header = (
        '<header class="document-header">'
        '<div class="ksef-brand"><div class="ksef-word">KSe<span class="ksef-red">F</span></div>'
        '<div class="ksef-subtitle">Krajowy System e-Faktur</div></div>'
        '<div class="invoice-meta">'
        '<span class="label">Numer faktury</span>'
        f'<div class="invoice-number">{number}</div>'
        '<div class="invoice-type">FAKTURA VAT</div>'
        f"{ksef_line}</div></header>"
    )
    parties = (
        '<section class="section" aria-label="Dane kontrahentów">'
        '<div class="parties">'
        + _party_card("Sprzedawca", data["seller"], data["seller_address"])
        + _party_card("Nabywca", data["buyer"], data["buyer_address"])
        + "</div></section>"
    )
    details = (
        '<section class="section"><h2 class="section-title">Szczegóły faktury</h2>'
        '<div class="details">'
        '<div><span class="detail-label">Data wystawienia</span>'
        f'<span class="detail-value">{_pl_date(data["issue_date"])}</span></div>'
        '<div><span class="detail-label">Waluta</span>'
        f'<span class="detail-value">{currency}</span></div>'
        + (
            '<div><span class="detail-label">Data dostawy lub wykonania usługi</span>'
            f'<span class="detail-value">{_pl_date(data["delivery_date"])}</span></div>'
            if data["delivery_date"]
            else ""
        )
        + "</div></section>"
    )
    line_rows = "".join(
        '<tr>'
        f'<td class="line-index">{_e(row["number"])}</td>'
        f'<td class="description">{_e(row["description"])}</td>'
        f'<td class="number">{_e(_pl_decimal(row["quantity"]))}</td>'
        f'<td>{_e(row["unit"]) if row["unit"] else "—"}</td>'
        f'<td class="number">{_e(_pl_decimal(row["unit_net"]))}</td>'
        f'<td>{_e(row["tax_rate"])}</td>'
        f'<td class="number">{_e(_pl_decimal(row["net"]))}</td>'
        "</tr>"
        for row in rows
    )
    items = (
        '<section class="section"><h2 class="section-title">Pozycje faktury</h2>'
        '<div class="table-wrap"><table class="items">'
        '<thead><tr><th class="col-nr">Lp.</th><th class="col-name">Nazwa towaru lub usługi</th>'
        '<th class="col-quantity number">Ilość</th><th class="col-unit">J.m.</th>'
        '<th class="col-price number">Cena netto</th><th class="col-vat">VAT</th>'
        '<th class="col-net number">Wartość netto</th></tr></thead>'
        f"<tbody>{line_rows}</tbody></table></div></section>"
    )
    vat_rows = "".join(
        '<tr>'
        f'<td>{_e(item["rate"] or "")}</td>'
        f'<td class="number">{_e(_pl_decimal(item["net"])) if item["net"] is not None else "—"}</td>'
        f'<td class="number">{_e(_pl_decimal(item["vat"])) if item["vat"] is not None else "—"}</td>'
        f'<td class="number">{_e(_gross_by_rate(item))}</td>'
        "</tr>"
        for item in summary
    )
    tax = (
        '<section class="section"><h2 class="section-title">Podsumowanie stawek VAT</h2>'
        '<div class="table-wrap"><table class="vat-summary">'
        '<thead><tr><th class="col-rate">Stawka</th>'
        '<th class="col-net number">Netto</th><th class="col-vat number">VAT</th>'
        '<th class="col-gross number">Brutto*</th></tr></thead>'
        f'<tbody>{vat_rows}</tbody></table></div>'
        '<p class="footnote" style="font-size:9px">'
        '* Brutto według stawki obliczono informacyjnie z wartości netto i VAT z XML; '
        'dla stawek 0% i zw jest równe netto. Suma do zapłaty pochodzi bezpośrednio z P_15.'
        '</p>'
        '<div class="amount-due"><span>Kwota należności ogółem:</span>'
        f'<strong>{_e(_pl_decimal(str(data["gross"])))} {currency}</strong></div>'
        '</section>'
    )
    payment_fields = (
        ("Termin płatności", "payment_due_date"),
        ("Forma płatności", "payment_form"),
        ("Rachunek bankowy", "bank_account"),
    )
    payment_rows = "".join(
        f"<tr><td>{_e(label)}</td><td>{_e(_pl_date(data[key]) if key == 'payment_due_date' else data[key])}</td></tr>"
        for label, key in payment_fields
        if data[key]
    )
    payment = (
        '<section class="section"><h2 class="section-title">Płatność</h2>'
        f'<table class="payments"><tbody>{payment_rows}</tbody></table></section>'
        if payment_rows
        else ""
    )
    extra_rows = "".join(
        f'<tr><td>{_e(item["key"])}</td><td>{_e(item["value"])}</td></tr>'
        for item in additional_descriptions
    )
    extra = (
        '<section class="section"><h2 class="section-title">Dodatkowe informacje</h2>'
        f'<table class="extra"><tbody>{extra_rows}</tbody></table></section>'
        if extra_rows
        else ""
    )
    footer = (
        '<footer class="paper-footer">Podgląd danych faktury ustrukturyzowanej FA(3). '
        'Sam podgląd nie potwierdza autentyczności faktury w KSeF.'
        '</footer>'
    )
    return (
        '<!doctype html>\n<html lang="pl"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>Faktura {number}</title><style>{_CSS}</style></head><body>'
        + header
        + parties
        + details
        + items
        + tax
        + payment
        + extra
        + footer
        + '</body></html>\n'
    )
