"""Command line interface for offline FA(3) HTML rendering.

Features (EN):
- Reads a local XML file and writes standalone HTML.

Funkcje (PL):
- Odczytuje lokalny plik XML i zapisuje samowystarczalny HTML.

File: src/render_doc/cli.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from render_doc.ksef_verification import KsefVerification
from render_doc.renderer import render_fa3_html


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="render-doc", description="Renderuj obsługiwaną fakturę FA(3) do HTML."
    )
    parser.add_argument("input", type=Path, help="Lokalny plik XML FA(3)")
    parser.add_argument("--output", required=True, type=Path, help="Docelowy plik HTML")
    parser.add_argument(
        "--template", choices=("default", "classic", "ksef"), default="default",
        help="Szablon wyglądu (domyślnie: dotychczasowy)",
    )
    parser.add_argument(
        "--ksef-number", help="Potwierdzony numer KSeF (razem z --qr-environment)"
    )
    parser.add_argument(
        "--qr-environment", choices=("TEST", "DEMO", "PROD"),
        help="Środowisko QR KOD I (tylko szablon ksef i potwierdzony numer)"
    )
    args = parser.parse_args()
    has_number = args.ksef_number is not None
    has_environment = args.qr_environment is not None
    if has_number != has_environment:
        parser.error("--ksef-number i --qr-environment muszą być podane razem")
    if has_number and args.template != "ksef":
        parser.error("Kod QR wymaga --template ksef")
    try:
        verification = (
            KsefVerification(args.qr_environment, args.ksef_number)
            if has_number else None
        )
        html = render_fa3_html(
            args.input.read_bytes(), template=args.template, verification=verification
        )
        args.output.write_text(html, encoding="utf-8", newline="\n")
    except (OSError, ValueError) as exc:
        print(f"render-doc: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
