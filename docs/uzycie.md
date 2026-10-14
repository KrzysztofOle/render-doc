# Użycie render-doc

## Publiczne API

```python
from pathlib import Path

from render_doc import render_fa3_html

html = render_fa3_html(Path("faktura.xml").read_bytes())
Path("faktura.html").write_text(html, encoding="utf-8")
```

Numer KSeF jest opcjonalnym metadatum od wywołującego. Przykład używa
syntetycznej wartości testowej, a nie rzeczywistego numeru:

```python
from render_doc import render_fa3_html

html = render_fa3_html(
    xml_bytes,
    ksef_number="5860000000-20261014-TEST",  # wartość syntetyczna
)
```

Pomijając `ksef_number`, zachowujesz dotychczasowe zachowanie API. Renderer nie
wyprowadza numeru z XML i nie komunikuje się z KSeF.

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

Obsługiwany jest wariant FA(3) `1-0E`, podstawowa faktura `VAT`, PLN oraz
wiele pozycji ze stawkami `23`, `8`, `5`, `0 KR`, `0 WDT` i `0 EX`. Warianty
0% są prezentowane oddzielnie (krajowy, WDT, eksport); `zw` i pozostałe kody
są odrzucane. W `Podmiot2` wymagane są pola `JST=2` i `GV=2`; oznaczają one,
że faktura nie dotyczy jednostki podrzędnej JST ani członka grupy VAT. Wartość
`1` oraz inne wartości są odrzucane. `Podmiot3` pozostaje nieobsługiwany.
Renderer pokazuje `P_2`, `P_1`, dane `Podmiot1`/`Podmiot2` oraz
pola wiersza `NrWierszaFa`, `P_7`, `P_8A`, `P_8B`, `P_9A`, `P_11`, `P_12`.
Opcjonalne `P_6` jest walidowane jako data FA(3) i wyświetlane osobno jako data
dostawy lub wykonania usługi, również gdy jest równe `P_1`. Akceptowany jest
zamknięty zestaw nieaktywnych oznaczeń `Adnotacje` (wartości `2` dla `P_16`,
`P_17`, `P_18`, `P_18A`, `P_23` oraz znaczniki `P_19N`, `P_22N`, `P_PMarzyN`
o wartości `1`); aktywne lub nieznane warianty są odrzucane. Ogólne wpisy
`DodatkowyOpis` z `Klucz` i `Wartosc` są prezentowane w kolejności źródłowej;
wpisy z `NrWiersza` pozostają nieobsługiwane.

Podsumowanie wartości netto i VAT pochodzi z `P_13_1`/`P_14_1` (23%),
`P_13_2`/`P_14_2` (8%) oraz `P_13_3`/`P_14_3` (5%). Dla wariantów 0% netto
pochodzi z `P_13_6_1` (krajowa), `P_13_6_2` (WDT) i `P_13_6_3` (eksport);
FA(3) nie przewiduje dla nich osobnych sumarycznych pól VAT. Należność ogółem
jest prezentowana z `P_15`. Brak sumarycznego pola wymaganego przez wykrytą
stawkę powoduje `UnsupportedDocumentError`. Renderer nie przelicza ani nie
sumuje kwot, a pozostałe elementy i warianty odrzuca. Nie waliduje pełnej
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
