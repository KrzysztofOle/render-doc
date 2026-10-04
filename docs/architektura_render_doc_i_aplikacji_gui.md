# Architektura Systemu: Biblioteka `render-doc` oraz Aplikacje Klienckie (GUI / CLI)

Dokument opisuje modularną architekturę systemu do wizualizacji faktur KSeF (XML). Projekt został podzielony na:
1. **`render-doc`**: Niezależną bibliotekę Python zawierającą logikę parsowania, detekcji wersji schematu oraz transformacji XSLT do HTML.
2. **`render-doc-gui` / CLI**: Aplikacje użytkownika końcowego korzystające z pakietu `render-doc`.

---

## 1. Diagram Architektury

```
+-------------------------------------------------------+
|                Aplikacje Klienckie                    |
|  +-----------------------+     +-------------------+  |
|  |   Aplikacja GUI       |     |   Skrypt CLI /    |  |
|  | (Tkinter/CustomTkinter) |     |   Web API (FastAPI)| |
|  +-----------+-----------+     +---------+---------+  |
+--------------|---------------------------|------------+
               | import render_doc         |
               v                           v
+-------------------------------------------------------+
|               Biblioteka `render-doc`                 |
|  +--------------------+     +----------------------+  |
|  | KSeFRenderer       |     | SchemaDetector       |  |
|  +---------+----------+     +----------+-----------+  |
|            |                           |              |
|            v                           v              |
|  +-------------------------------------------------+  |
|  |           Silnik XSLT (lxml)                    |  |
|  |  [ Wbudowane zasoby XSLT: FA(1), FA(2), ... ]    |  |
|  +-------------------------------------------------+  |
+-------------------------------------------------------+
```

---

## 2. Biblioteka `render-doc` (Core Package)

### 2.1 Struktura katalogów biblioteki

```
render_doc/
├── pyproject.toml               # Konfiguracja pakietowania (Flit / Hatch / Setuptools)
├── README.md
└── src/
    └── render_doc/
        ├── __init__.py          # Główny interfejs API biblioteki
        ├── exceptions.py        # Dedykowane wyjątki
        ├── detector.py          # Logika rozpoznawania przestrzeni nazw XML
        ├── renderer.py          # Główna klasa KSeFRenderer
        └── resources/           # Wbudowane szablony XSLT
            ├── FA_1.xslt
            └── FA_2.xslt
```

### 2.2 Kod źródłowy biblioteki

#### `src/render_doc/exceptions.py`
```python
class RenderDocError(Exception):
    """Bazowy wyjątek dla biblioteki render-doc."""
    pass

class UnsupportedSchemaError(RenderDocError):
    """Rzucany, gdy przestrzeń nazw XML faktury nie jest obsługiwana."""
    pass

class XSLTNotFoundError(RenderDocError):
    """Rzucany, gdy brakuje odpowiedniego arkusza XSLT."""
    pass
```

#### `src/render_doc/detector.py`
```python
from lxml import etree
from .exceptions import UnsupportedSchemaError

# Mapowanie namespace XML KSeF na nazwy zasobów XSLT
KNOWN_NAMESPACES = {
    "http://crd.gov.pl/wzor/2021/11/29/11089/": "FA_1.xslt",
    "http://crd.gov.pl/wzor/2023/06/29/12648/": "FA_2.xslt",
}

class SchemaDetector:
    @staticmethod
    def detect_xslt_filename(xml_bytes: bytes) -> str:
        """Rozpoznaje wersję schematu KSeF na podstawie przestrzeni nazw (xmlns)."""
        try:
            parser = etree.XMLParser(recover=True)
            root = etree.fromstring(xml_bytes, parser=parser)
            namespace = root.nsmap.get(None)

            if not namespace or namespace not in KNOWN_NAMESPACES:
                raise UnsupportedSchemaError(f"Nieobsługiwana lub brakująca przestrzeń nazw XML: {namespace}")

            return KNOWN_NAMESPACES[namespace]
        except etree.XMLSyntaxError as e:
            raise UnsupportedSchemaError(f"Niepoprawny plik XML: {e}")
```

#### `src/render_doc/renderer.py`
```python
from pathlib import Path
from typing import Union
import importlib.resources
from lxml import etree

from .detector import SchemaDetector
from .exceptions import XSLTNotFoundError

class KSeFRenderer:
    """Główna klasa odpowiadająca za renderowanie faktur KSeF do formatu HTML."""

    def __init__(self, custom_xslt_dir: Union[Path, str, None] = None):
        self.custom_xslt_dir = Path(custom_xslt_dir) if custom_xslt_dir else None

    def _get_xslt_content(self, xslt_filename: str) -> bytes:
        """Pobiera zawartość pliku XSLT z dostosowanego katalogu lub z wbudowanych zasobów pakietu."""
        if self.custom_xslt_dir:
            custom_file = self.custom_xslt_dir / xslt_filename
            if custom_file.exists():
                return custom_file.read_bytes()

        # Pobieranie z wbudowanych zasobów pakietu (importlib.resources)
        try:
            res_path = importlib.resources.files("render_doc.resources").joinpath(xslt_filename)
            return res_path.read_bytes()
        except Exception as e:
            raise XSLTNotFoundError(f"Nie znaleziono szablonu XSLT '{xslt_filename}': {e}")

    def render_xml_to_html(self, xml_content: Union[str, bytes]) -> str:
        """Przekształca surowy tekst/bajty XML faktury na ciąg HTML."""
        xml_bytes = xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content

        # 1. Detekcja schematu
        xslt_filename = SchemaDetector.detect_xslt_filename(xml_bytes)

        # 2. Wczytanie XSLT
        xslt_bytes = self._get_xslt_content(xslt_filename)

        # 3. Transformacja XSLT
        xml_doc = etree.fromstring(xml_bytes)
        xslt_doc = etree.fromstring(xslt_bytes)

        transform = etree.XSLT(xslt_doc)
        result_tree = transform(xml_doc)

        return str(result_tree)

    def render_file_to_html_file(self, xml_file_path: Union[Path, str], output_html_path: Union[Path, str]) -> Path:
        """Przetwarza plik XML z dysku i zapisuje wynikowy plik HTML."""
        xml_path = Path(xml_file_path)
        out_path = Path(output_html_path)

        xml_bytes = xml_path.read_bytes()
        html_str = self.render_xml_to_html(xml_bytes)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html_str, encoding="utf-8")

        return out_path
```

#### `src/render_doc/__init__.py`
```python
from .renderer import KSeFRenderer
from .exceptions import RenderDocError, UnsupportedSchemaError, XSLTNotFoundError

__version__ = "0.1.0"
__all__ = ["KSeFRenderer", "RenderDocError", "UnsupportedSchemaError", "XSLTNotFoundError"]
```

---

## 3. Aplikacja Graficzna (GUI Client)

Aplikacja z interfejsem użytkownika importuje pakiet `render_doc` i zapewnia wygodne przeciąganie plików (Drag & Drop) lub wybór pliku przyciskiem, a następnie automatyczne otwieranie wyrenderowanego podglądu w przeglądarce.

### Wymagania GUI:
* `customtkinter` (nowoczesny wygląd Tkinter)
* `webbrowser` (do otwierania przeglądarki)

### Przykładowy kod `gui_app.py`:

```python
import os
import sys
import tempfile
import webbrowser
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Import naszej biblioteki
from render_doc import KSeFRenderer, RenderDocError

class KSeFViewerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("KSeF Faktura Viewer (render-doc GUI)")
        self.geometry("500x300")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.renderer = KSeFRenderer()

        # Układ elementów
        self.label = ctk.CTkLabel(
            self, 
            text="Wybierz plik XML faktury KSeF\naby otworzyć podgląd HTML", 
            font=("Arial", 16)
        )
        self.label.pack(pady=40)

        self.btn_select = ctk.CTkButton(
            self, 
            text="Otwórz plik XML...", 
            command=self.select_and_render_file
        )
        self.btn_select.pack(pady=10)

        self.status_label = ctk.CTkLabel(self, text="", font=("Arial", 12), text_color="gray")
        self.status_label.pack(pady=20)

    def select_and_render_file(self):
        file_path = filedialog.askopenfilename(
            title="Wybierz fakturę KSeF XML",
            filetypes=[("Pliki XML", "*.xml"), ("Wszystkie pliki", "*.*")]
        )

        if not file_path:
            return

        try:
            self.status_label.configure(text="Przetwarzanie...", text_color="blue")
            self.update_idletasks()

            # Zapis podglądu do katalogu tymczasowego
            temp_dir = Path(tempfile.gettempdir()) / "ksef_views"
            output_html = temp_dir / f"{Path(file_path).stem}.html"

            # Użycie biblioteki render-doc
            self.renderer.render_file_to_html_file(file_path, output_html)

            # Otwarcie w przeglądarce
            webbrowser.open(output_html.resolve().as_uri())
            
            self.status_label.configure(
                text=f"Sukces! Otwarto podgląd: {output_html.name}", 
                text_color="green"
            )

        except RenderDocError as e:
            messagebox.showerror("Błąd konwersji KSeF", str(e))
            self.status_label.configure(text="Błąd przetwarzania.", text_color="red")
        except Exception as e:
            messagebox.showerror("Błąd niespodziewany", f"Wystąpił błąd: {e}")
            self.status_label.configure(text="Błąd systemowy.", text_color="red")

if __name__ == "__main__":
    app = KSeFViewerApp()
    app.mainloop()
```

---

## 4. Przykład Użycia CLI / Skryptu konsolowego

Dzięki wydzieleniu biblioteki można w prosty sposób stworzyć również narzędzie do pracy w konsoli:

```python
# cli_app.py
import sys
import webbrowser
from pathlib import Path
from render_doc import KSeFRenderer

def main():
    if len(sys.argv) < 2:
        print("Użycie: python cli_app.py <sciezka_do_faktury.xml>")
        sys.exit(1)

    xml_path = Path(sys.argv[1])
    output_html = Path("output") / f"{xml_path.stem}.html"

    renderer = KSeFRenderer()
    
    print(f"Renderowanie {xml_path}...")
    renderer.render_file_to_html_file(xml_path, output_html)
    
    print(f"Wygenerowano: {output_html.resolve()}")
    webbrowser.open(output_html.resolve().as_uri())

if __name__ == "__main__":
    main()
```

---

## 5. Korzyści z rozdzielenia na bibliotekę `render-doc`

1. **Reużywalność (Reusability):** Bibliotekę `render-doc` można łatwo zainstalować przez `pip` w dowolnym innym projekcie Python (np. serwerze webowym Django/FastAPI, automatycznym konwerterze mailowym, botach księgowych).
2. **Łatwość testowania (Testability):** Logikę transformacji XML $\rightarrow$ HTML można testować jednostkowo (`pytest`) bez konieczności uruchamiania interfejsu graficznego.
3. **Izolacja odpowiedzialności:** Zmiany w wyglądzie interfejsu GUI nie wpływają na silnik konwersji i vice versa.