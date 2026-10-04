# Architektura Systemu: Biblioteka `render-doc` oraz Aplikacje Klienckie (GUI / CLI)

Dokument opisuje modularną architekturę systemu do wizualizacji dokumentów KSeF (XML). Projekt obsługuje wszystkie typy dokumentów KSeF oraz jest przygotowany na rozwój o format wyjściowy PDF.

## 1. Założenia i Rozszerzalność

1. **Pełna obsługa dokumentów KSeF:**
   * Faktury VAT/Korygujące: `FA(1)`, `FA(2)`, `FA(3)` (i kolejne).
   * Faktury VAT RR: `FA_RR(1)`.
   * Urzędowe Poświadczenia Odbioru: `UPO`.
2. **Architektura pod wieloformatowość:**
   * **HTML (Priorytet 1)**: Domyślna i bezpośrednia transformacja XSLT.
   * **PDF (Priorytet 2 / Przyszłość)**: Dedykowany moduł eksportu (np. bazujący na `WeasyPrint` lub `Playwright`), wywoływany przez spójny interfejs API.

---

## 2. Diagram Architektury

```
+-------------------------------------------------------+
|                Aplikacje Klienckie                    |
|  +-----------------------+     +-------------------+  |
|  |     Aplikacja GUI     |     |   Skrypt CLI /    |  |
|  | (CustomTkinter / App) |     |  REST API (FastAPI)| |
|  +-----------+-----------+     +---------+---------+  |
+--------------|---------------------------|------------+
               | import render_doc         |
               v                           v
+-------------------------------------------------------+
|               Biblioteka `render-doc`                 |
|                                                       |
|  +-------------------------------------------------+  |
|  |                   KSeFRenderer                  |  |
|  |   - render_to_html(...)                         |  |
|  |   - render_to_pdf(...)  [Planowane]             |  |
|  +---------+-------------------+-------------------+  |
|            |                   |                      |
|            v                   v                      |
|  +-------------------+   +-------------------------+  |
|  |  SchemaDetector   |   |   Exporters Strategy    |  |
|  | (FA, FA_RR, UPO)  |   | - HTMLExporter (XSLT)   |  |
|  +-------------------+   | - PDFExporter (Future)  |  |
|                          +-------------------------+  |
+-------------------------------------------------------+
```

---

## 3. Struktura Katalogów Biblioteki `render-doc`

```
render_doc/
├── pyproject.toml               # Konfiguracja pakietowania
├── README.md
└── src/
    └── render_doc/
        ├── __init__.py          # Główny interfejs API
        ├── enums.py             # Typy dokumentów i formaty wyjściowe
        ├── exceptions.py        # Wyjątki
        ├── detector.py          # Automatyczna detekcja typu dokumentu KSeF
        ├── renderer.py          # Klasa orchestratora KSeFRenderer
        ├── exporters/           # Silniki wyjściowe (HTML, PDF)
        │   ├── __init__.py
        │   ├── base.py          # Interfejs abstrakcyjny BaseExporter
        │   ├── html_exporter.py # Transformator XSLT do HTML
        │   └── pdf_exporter.py  # [Future] Konwerter HTML -> PDF
        └── resources/           # Szablony XSLT dla wszystkich typów dokumentów
            ├── FA_1.xslt
            ├── FA_2.xslt
            ├── FA_RR_1.xslt
            └── UPO.xslt
```

---

## 4. Kod Źródłowy Biblioteki (Prototyp Modułów)

### 4.1 Enumy i Wyjątki (`enums.py`, `exceptions.py`)

```python
# src/render_doc/enums.py
from enum import Enum, auto

class KSeFDocType(Enum):
    FA_1 = "FA(1)"
    FA_2 = "FA(2)"
    FA_RR_1 = "FA_RR(1)"
    UPO = "UPO"
    UNKNOWN = "UNKNOWN"

class OutputFormat(Enum):
    HTML = "html"
    PDF = "pdf"
```

```python
# src/render_doc/exceptions.py
class RenderDocError(Exception):
    """Bazowy wyjątek dla biblioteki render-doc."""
    pass

class UnsupportedSchemaError(RenderDocError):
    """Rzucany, gdy przestrzeń nazw XML nie odpowiada żadnemu znanemu schematowi KSeF."""
    pass

class ExportError(RenderDocError):
    """Błąd podczas generowania pliku wyjściowego (HTML/PDF)."""
    pass
```

---

### 4.2 Detektor Schematów KSeF (`detector.py`)

Rozpoznaje typ dokumentu (faktura podstawowa, faktura RR, poświadczenie UPO) na podstawie root tagu oraz przestrzeni nazw (xmlns):

```python
# src/render_doc/detector.py
from lxml import etree
from .enums import KSeFDocType
from .exceptions import UnsupportedSchemaError

# Mapa przestrzeni nazw (xmlns) oraz tagów głównych na typy dokumentów KSeF
NAMESPACE_MAP = {
    # Faktury VAT
    "http://crd.gov.pl/wzor/2021/11/29/11089/": (KSeFDocType.FA_1, "FA_1.xslt"),
    "http://crd.gov.pl/wzor/2023/06/29/12648/": (KSeFDocType.FA_2, "FA_2.xslt"),
    
    # Faktury RR
    "http://crd.gov.pl/wzor/2024/02/08/13310/": (KSeFDocType.FA_RR_1, "FA_RR_1.xslt"),
    
    # UPO (Urzędowe Poświadczenie Odbioru)
    "http://ksef.mf.gov.pl/schema/gtw/svc/types/2021/10/01/0001": (KSeFDocType.UPO, "UPO.xslt"),
    "http://crd.gov.pl/wzor/2023/12/19/13143/": (KSeFDocType.UPO, "UPO.xslt"),
}

class DocumentInfo:
    def __init__(self, doc_type: KSeFDocType, xslt_filename: str):
        self.doc_type = doc_type
        self.xslt_filename = xslt_filename

class SchemaDetector:
    @staticmethod
    def detect(xml_bytes: bytes) -> DocumentInfo:
        """Skanuje plik XML i zwraca rozpoznany typ dokumentu oraz przypisany plik XSLT."""
        try:
            parser = etree.XMLParser(recover=True)
            root = etree.fromstring(xml_bytes, parser=parser)
            namespace = root.nsmap.get(None)

            if namespace in NAMESPACE_MAP:
                doc_type, xslt_file = NAMESPACE_MAP[namespace]
                return DocumentInfo(doc_type, xslt_file)

            # Próba weryfikacji po tagu głównym (fallback np. dla UPO)
            tag_name = etree.QName(root).localname
            if tag_name == "Potwierdzenie" or tag_name == "UPO":
                return DocumentInfo(KSeFDocType.UPO, "UPO.xslt")

            raise UnsupportedSchemaError(f"Nieobsługiwany dokument KSeF (xmlns: {namespace}, tag: {tag_name})")
        except etree.XMLSyntaxError as e:
            raise UnsupportedSchemaError(f"Błąd składni XML: {e}")
```

---

### 4.3 Silnik Eksportu (`exporters/`)

Stosujemy wzorzec **Strategii** – oddzielamy silnik renderowania HTML od przyszłego modułu generowania PDF.

```python
# src/render_doc/exporters/base.py
from abc import ABC, abstractmethod
from typing import Union
from pathlib import Path

class BaseExporter(ABC):
    @abstractmethod
    def export(self, xml_bytes: bytes, xslt_bytes: bytes) -> str:
        """Przekształca XML do postaci tekstowej (np. HTML)."""
        pass
```

```python
# src/render_doc/exporters/html_exporter.py
from lxml import etree
from .base import BaseExporter
from ..exceptions import ExportError

class HTMLExporter(BaseExporter):
    def export(self, xml_bytes: bytes, xslt_bytes: bytes) -> str:
        try:
            xml_doc = etree.fromstring(xml_bytes)
            xslt_doc = etree.fromstring(xslt_bytes)
            
            transform = etree.XSLT(xslt_doc)
            result_tree = transform(xml_doc)
            return str(result_tree)
        except Exception as e:
            raise ExportError(f"Błąd transformacji XSLT do HTML: {e}")
```

```python
# src/render_doc/exporters/pdf_exporter.py
# [Moduł przygotowany pod przyszły rozwój]
from .base import BaseExporter
from ..exceptions import ExportError

class PDFExporter(BaseExporter):
    def export(self, xml_bytes: bytes, xslt_bytes: bytes) -> bytes:
        """
        Planowana implementacja:
        1. Wygenerowanie HTML przy użyciu HTMLExporter.
        2. Przekształcenie HTML na PDF (np. za pomocą WeasyPrint, Playwright lub pdfkit).
        """
        raise NotImplementedError("Eksport do formatu PDF będzie dostępny w kolejnej wersji biblioteki.")
```

---

### 4.4 Główny Interfejs `KSeFRenderer` (`renderer.py`)

```python
# src/render_doc/renderer.py
from pathlib import Path
from typing import Union, Optional
import importlib.resources

from .detector import SchemaDetector
from .enums import OutputFormat, KSeFDocType
from .exceptions import XSLTNotFoundError, RenderDocError
from .exporters.html_exporter import HTMLExporter
from .exporters.pdf_exporter import PDFExporter

class KSeFRenderer:
    """Główna klasa fasady do obsługi wizualizacji dokumentów KSeF."""

    def __init__(self, custom_xslt_dir: Optional[Union[Path, str]] = None):
        self.custom_xslt_dir = Path(custom_xslt_dir) if custom_xslt_dir else None
        self.html_exporter = HTMLExporter()
        self.pdf_exporter = PDFExporter()

    def _load_xslt(self, xslt_filename: str) -> bytes:
        if self.custom_xslt_dir:
            custom_file = self.custom_xslt_dir / xslt_filename
            if custom_file.exists():
                return custom_file.read_bytes()

        try:
            res_path = importlib.resources.files("render_doc.resources").joinpath(xslt_filename)
            return res_path.read_bytes()
        except Exception as e:
            raise XSLTNotFoundError(f"Nie odnaleziono szablonu XSLT '{xslt_filename}': {e}")

    def render(self, xml_content: Union[str, bytes], fmt: OutputFormat = OutputFormat.HTML) -> Union[str, bytes]:
        """Uniwersalna metoda renderująca dokument do wskazanego formatu."""
        xml_bytes = xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content
        doc_info = SchemaDetector.detect(xml_bytes)
        xslt_bytes = self._load_xslt(doc_info.xslt_filename)

        if fmt == OutputFormat.HTML:
            return self.html_exporter.export(xml_bytes, xslt_bytes)
        elif fmt == OutputFormat.PDF:
            return self.pdf_exporter.export(xml_bytes, xslt_bytes)
        else:
            raise RenderDocError(f"Nieobsługiwany format wyjściowy: {fmt}")

    def render_file_to_file(
        self, 
        xml_path: Union[Path, str], 
        output_path: Union[Path, str], 
        fmt: OutputFormat = OutputFormat.HTML
    ) -> Path:
        """Wczytuje plik XML z dysku i zapisuje wygenerowany wynik (HTML/PDF)."""
        xml_p = Path(xml_path)
        out_p = Path(output_path)

        result = self.render(xml_p.read_bytes(), fmt=fmt)

        out_p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(result, str):
            out_p.write_text(result, encoding="utf-8")
        else:
            out_p.write_bytes(result)

        return out_p
```

---

## 5. Przykładowa Integracja w GUI (`gui_app.py`)

Aplikacja kliencka rozpoznaje typ pliku i wyświetla odpowiedni komunikat oraz pozwala na wybór opcji podglądu:

```python
import tempfile
import webbrowser
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox

from render_doc import KSeFRenderer, OutputFormat, RenderDocError

class KSeFMultiDocApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("KSeF Universal Document Viewer")
        self.geometry("550x350")
        
        self.renderer = KSeFRenderer()

        self.label = ctk.CTkLabel(
            self, 
            text="Przeglądarka Dokumentów KSeF\n(Faktury FA, FA_RR oraz UPO)", 
            font=("Arial", 16, "bold")
        )
        self.label.pack(pady=30)

        self.btn_select = ctk.CTkButton(
            self, 
            text="Wybierz plik XML (FA / UPO)...", 
            command=self.process_file
        )
        self.btn_select.pack(pady=15)

        self.status_label = ctk.CTkLabel(self, text="Gotowy", font=("Arial", 12), text_color="gray")
        self.status_label.pack(pady=20)

    def process_file(self):
        file_path = filedialog.askopenfilename(
            title="Wybierz dokument KSeF (XML)",
            filetypes=[("Pliki XML", "*.xml")]
        )
        if not file_path:
            return

        try:
            # Zapis wyrenderowanego podglądu HTML do folderu tymczasowego
            temp_dir = Path(tempfile.gettempdir()) / "ksef_docs_view"
            out_html = temp_dir / f"{Path(file_path).stem}.html"

            # Renderowanie przy użyciu biblioteki
            self.renderer.render_file_to_file(file_path, out_html, fmt=OutputFormat.HTML)

            # Otwarcie w domyślnej przeglądarce
            webbrowser.open(out_html.resolve().as_uri())
            
            self.status_label.configure(
                text=f"Wyrenderowano i otwarto: {out_html.name}", 
                text_color="green"
            )
        except RenderDocError as e:
            messagebox.showerror("Błąd KSeF", str(e))
            self.status_label.configure(text="Błąd dokumentu.", text_color="red")

if __name__ == "__main__":
    app = KSeFMultiDocApp()
    app.mainloop()
```

---

## 6. Podsumowanie Wprowadzonych Zmian

1. **Obsługa wszystkich schematów KSeF:** `SchemaDetector` klasyfikuje dokumenty na podstawie ich unikalnych przestrzeni nazw oraz tagów korzenia XML (`FA_1`, `FA_2`, `FA_RR_1`, `UPO`).
2. **Gotowość na eksport PDF:** Wprowadzono enum `OutputFormat` oraz wzorzec Exportera. Przyszłe wdrożenie generatora PDF sprowadzi się do zaimplementowania klasy `PDFExporter` bez konieczności przebudowywania aplikacji GUI czy interfejsu API.
3. **Elastyczność zasobów:** Możliwość dodawania kolejnych arkuszy stylów XSLT bezpośrednio w folderze `resources/`.