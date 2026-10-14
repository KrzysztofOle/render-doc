# Użycie render-doc

## Publiczne API

```python
from pathlib import Path

from render_doc import render_fa3_html

html = render_fa3_html(Path("faktura.xml").read_bytes())
Path("faktura.html").write_text(html, encoding="utf-8")
```

Funkcja przyjmuje `bytes` i zwraca kompletny dokument HTML w `str`. Błędny
XML powoduje `InvalidXmlError`; poprawny składniowo dokument spoza obsługiwanego
profilu powoduje `UnsupportedDocumentError`. Wyjątki można importować z
`render_doc`.

## CLI

Po instalacji pakietu:

```sh
render-doc faktura.xml --output faktura.html
```

Polecenie czyta lokalny plik, wywołuje publiczne API i zapisuje wynik UTF-8.
Kod zakończenia `0` oznacza powodzenie, `2` błąd odczytu, zapisu, parsowania
lub nieobsługiwany dokument.

## Profil danych

Obsługiwany jest wariant FA(3) `1-0E`, podstawowa faktura `VAT`, PLN i pozycje
ze stawką `23`. Renderer pokazuje `P_2`, `P_1`, dane identyfikacyjne
`Podmiot1`/`Podmiot2`, pola pozycji `P_7`, `P_8A`, `P_8B`, `P_9A`, `P_11`,
`P_12` oraz wartości zbiorcze `P_13_1`, `P_14_1`, `P_15` (należność ogółem,
odpowiadająca wartości brutto w obsługiwanym profilu). Nie przelicza kwot.
Nieobsługiwane elementy są odrzucane. Renderer nie wykonuje walidacji pełnej
zgodności z XSD FA(3).

HTML zawiera wyłącznie wbudowany CSS, bez JavaScriptu, fontów, obrazów ani
odwołań do zewnętrznych zasobów. Zgodność z Optimą, w szczególności z
`CDN.DokumentyKSeF.DKF_Html`, wymaga osobnego testu w Optimie.

## Testy offline

```sh
python -m pytest -q
```

Testy korzystają z syntetycznego XML; nie odczytują ani nie zapisują danych
klientów i nie łączą się z siecią.
