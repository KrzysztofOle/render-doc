"""Public API for offline FA(3) HTML rendering.

Features (EN):
- Exposes the versioned package API.

Funkcje (PL):
- Udostępnia wersjonowane API pakietu.

File: src/render_doc/__init__.py
"""

from render_doc.renderer import (
    InvalidXmlError,
    RenderDocError,
    UnsupportedDocumentError,
    render_fa3_html,
)

__all__ = [
    "InvalidXmlError",
    "RenderDocError",
    "UnsupportedDocumentError",
    "render_fa3_html",
]
__version__ = "0.2.0"
