# Plan Działania: Aplikacja Python do konwersji faktur KSeF (XML) na podgląd HTML

Dokument zawiera kompletny plan architektoniczny i instrukcję wdrożenia aplikacji skryptowej/webowej w języku Python, służącej do przekształcania ustrukturyzowanych faktur KSeF (format XML) do czytelnej postaci HTML z wykorzystaniem oficjalnych szablonów XSLT.

---

## 1. Cel i założenia projektu

- **Główny cel:** Automatyczna konwersja plików faktur KSeF w formacie XML (dla schematów `FA(1)` oraz `FA(2)`) do czytelnych plików HTML.
- **Funkcja podglądu:** Automatyczne otwieranie wygenerowanego pliku HTML w domyślnej przeglądarce internetowej użytkownika.
- **Detekcja wersji:** Automatyczne rozpoznawanie struktury logicznej faktury (FA_1 vs FA_2) na podstawie przestrzeni nazw (namespace) w pliku XML i dobór odpowiedniego arkusza stylów XSLT.

---

## 2. Wymagania wstępne i biblioteki

Do realizacji projektu zalecane jest środowisko **Python 3.9+**.

### Wymagane pakiety Python:
- **`lxml`**: Szybka i wydajna biblioteka do obsługi XML oraz przetwarzania transformat XSLT 1.0.
- **`webbrowser`**: Standardowa biblioteka Pythona do automatycznego uruchamiania przeglądarki.
- **`pathlib` / `os`**: Do zarządzania ścieżkami plików na dysku.

### Instalacja zależności:
```bash
pip install lxml
```

---

## 3. Pozyskanie szablonów XSLT

Do prawidłowego wyrenderowania faktury KSeF niezbędne są oficjalne arkusze stylów XSLT opublikowane przez Ministerstwo Finansów.

1. Pobierz pliki stylów `.xslt` z oficjalnego repozytorium MF na GitHubie (np. `ksef-docs` lub `ksef-pdf-generator`) bądź z portalu ePUAP (CRWDE).
2. Zapisz je w strukturze projektu w katalogu `schematy/`:
   - `schematy/FA_1.xslt` (dla schematu Wzór FA(1))
   - `schematy/FA_2.xslt` (dla schematu Wzór FA(2))

---

## 4. Architektura i plan wdrożenia krok po kroku

### Krok 1: Struktura katalogów projektu
Utwórz następujący układ plików:
```text
ksef_converter/
│
├── schematy/
│   ├── FA_1.xslt
│   └── FA_2.xslt
│
├── input/             # Folder na pliki XML do przetworzenia
├── output/            # Folder na wygenerowane pliki HTML
├── main.py            # Główny skrypt aplikacji
└── requirements.txt   # Zależności projektu
```

---

### Krok 2: Detekcja schematu XML
Faktura KSeF posiada główny element z określoną przestrzenią nazw (`xmlns`). Aplikacja musi odczytać nagłówek XML i wykryć wersję faktury:
- `http://crd.gov.pl/wzor/2021/11/29/11089/` $\rightarrow$ **FA(1)**
- `http://crd.gov.pl/wzor/2023/06/29/12648/` $\rightarrow$ **FA(2)**

---

### Krok 3: Silnik transformacji XSLT (`lxml`)
Moduł odpowiedzialny za wczytanie pliku XML oraz właściwego pliku XSLT, wykonanie operacji `XSLT()` i wygenerowanie kodu HTML.

---

### Krok 4: Podgląd w przeglądarce
Wykorzystanie modułu `webbrowser.open()` do uruchomienia pliku wyjściowego HTML w domyślnej przeglądarce systemowej.

---

## 5. Przykładowa implementacja kodu (`main.py`)

```python
import os
import sys
import webbrowser
from pathlib import Path
from lxml import etree

# Mapowanie przestrzeni nazw XML na pliki XSLT
XSLT_MAPPING = {
    "http://crd.gov.pl/wzor/2021/11/29/11089/": "schematy/FA_1.xslt",
    "http://crd.gov.pl/wzor/2023/06/29/12648/": "schematy/FA_2.xslt"
}

def wykryj_xslt(xml_tree: etree._ElementTree) -> Path:
    """Wykrywa właściwy plik XSLT na podstawie namespace w pliku XML."""
    root = xml_tree.getroot()
    # Pobranie głównej przestrzeni nazw
    namespace = root.nsmap.get(None)
    
    if namespace in XSLT_MAPPING:
        xslt_path = Path(XSLT_MAPPING[namespace])
        if xslt_path.exists():
            return xslt_path
        else:
            raise FileNotFoundError(f"Brak pliku XSLT: {xslt_path}")
    else:
        raise ValueError(f"Nieobsługiwana przestrzeń nazw XML: {namespace}")

def konwertuj_xml_do_html(xml_path: Path, output_dir: Path) -> Path:
    """Konwertuje plik XML faktury KSeF do formatu HTML."""
    if not xml_path.exists():
        raise FileNotFoundError(f"Plik XML nie istnieje: {xml_path}")

    # 1. Wczytanie pliku XML
    parser = etree.XMLParser(remove_blank_text=True)
    xml_tree = etree.parse(str(xml_path), parser)

    # 2. Wykrycie odpowiedniego arkusza XSLT
    xslt_path = wykryj_xslt(xml_tree)
    xslt_tree = etree.parse(str(xslt_path))

    # 3. Wykonanie transformacji
    transform = etree.XSLT(xslt_tree)
    html_tree = transform(xml_tree)

    # 4. Zapis do pliku HTML
    output_dir.mkdir(parents=True, exist_ok=True)
    output_html_path = output_dir / f"{xml_path.stem}.html"
    
    with open(output_html_path, "wb") as f:
        f.write(etree.tostring(html_tree, pretty_print=True, method="html", encoding="utf-8"))

    return output_html_path

def otworz_w_przegladarce(html_path: Path):
    """Otwiera plik HTML w domyślnej przeglądarce."""
    absolute_url = html_path.resolve().as_uri()
    print(f"Otwieranie w przeglądarce: {absolute_url}")
    webbrowser.open(absolute_url)

def main():
    if len(sys.argv) < 2:
        print("Użycie: python main.py <sciezka_do_pliku_xml>")
        return

    xml_file = Path(sys.argv[1])
    output_folder = Path("output")

    try:
        print(f"Przetwarzanie pliku: {xml_file.name}...")
        html_file = konwertuj_xml_do_html(xml_file, output_folder)
        print(f"Wygenerowano plik HTML: {html_file}")
        otworz_w_przegladarce(html_file)
    except Exception as e:
        print(f"Błąd podczas konwersji: {e}")

if __name__ == "__main__":
    main()
```

---

## 6. Rozbudowa i dalsze możliwości (Roadmap)

1. **Interfejs graficzny (GUI):**
   - Dodanie prostego okna w **Tkinter** lub **PyQt** z przyciskiem „Wybierz plik XML” i automatycznym podglądem.
2. **Eksport do PDF:**
   - Integracja z biblioteką `weasyprint` lub `pdfkit` (wkhtmltopdf), aby wygenerowany HTML zamienić od razu na gotowy dokument PDF gotowy do druku.
3. **Generowanie kodów QR:**
   - Dodanie modułu w Pythonie (`qrcode`), który wygeneruje kod QR dla faktury KSeF (zgodnie z wymogami MF) i wstrzyknie go do wynikowego dokumentu HTML/PDF.
4. **Tryb masowy (Batch processing):**
   - Obsługa całych katalogów z plikami XML – zbiorcza konwersja do HTML dla całej paczki pobranej z KSeF.