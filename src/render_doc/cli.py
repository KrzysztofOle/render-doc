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

from render_doc.renderer import RenderDocError, render_fa3_html


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="render-doc", description="Renderuj obsługiwaną fakturę FA(3) do HTML."
    )
    parser.add_argument("input", type=Path, help="Lokalny plik XML FA(3)")
    parser.add_argument("--output", required=True, type=Path, help="Docelowy plik HTML")
    parser.add_argument(
        "--template", choices=("default", "classic"), default="default",
        help="Szablon wyglądu (domyślnie: dotychczasowy)",
    )
    args = parser.parse_args()
    try:
        html = render_fa3_html(args.input.read_bytes(), template=args.template)
        args.output.write_text(html, encoding="utf-8", newline="\n")
    except (OSError, RenderDocError) as exc:
        print(f"render-doc: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
