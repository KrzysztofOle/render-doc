# render-doc

Samodzielny pakiet Python do lokalnego renderowania ograniczonego profilu
podstawowej faktury KSeF FA(3) do kompletnego HTML. Renderowanie działa
offline i nie wymaga KSeF_2 ani Comarch ERP Optima.

## Obsługiwany zakres

Obsługiwany profil obejmuje dokument z nagłówkiem FA(3), podstawową fakturę
`RodzajFaktury=VAT`, walutę PLN oraz wiele pozycji ze stawkami VAT 23%, 8%, 5%
i 0%. Warianty 0% są rozróżniane jako `0 KR` (sprzedaż krajowa), `0 WDT`
(wewnątrzwspólnotowa dostawa towarów) i `0 EX` (eksport); inne oznaczenia, w
tym `zw`, są odrzucane. Wyświetla numer
`P_2`, datę wystawienia `P_1`, nazwę i NIP stron z `Podmiot1` i `Podmiot2`,
opcjonalne pojedyncze linie adresu, opis pozycji `P_7`, ilość `P_8B`, jednostkę
`P_8A`, cenę jednostkową netto `P_9A`, wartość netto pozycji `P_11`, źródłowy
numer `NrWierszaFa` i stawkę `P_12`. Podsumowanie pokazuje netto i VAT z pól
`P_13_1`/`P_14_1` (23%), `P_13_2`/`P_14_2` (8%) i `P_13_3`/`P_14_3` (5%).
Dla wariantów 0% pokazuje netto z `P_13_6_1`, `P_13_6_2` i `P_13_6_3`; FA(3)
nie definiuje dla nich osobnych sumarycznych pól VAT. Należność ogółem jest
prezentowana z `P_15` bez przeliczania.

To ograniczony profil, a nie walidator XSD ani pełna obsługa FA(3). Renderer
odrzuca inne waluty, stawki i warianty 0%, rodzaje faktury, dodatkowe pola i warianty, które
mogłyby zmienić znaczenie prezentacji. Nie obsługuje faktur korygujących,
zaliczkowych, uproszczonych, marży, rabatów ani kategorii VAT poza wskazanymi
powyżej. Inne struktury KSeF i dane dodatkowe nie są obecnie prezentowane. HTML jest
samowystarczalny, używa osadzonego CSS, nie zawiera JavaScriptu ani zasobów
zewnętrznych. Nie deklarujemy zgodności z generatorem MF ani z polem
`CDN.DokumentyKSeF.DKF_Html` Optimy.

## Instalacja

W Pythonie 3.10 lub nowszym, w katalogu repozytorium:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

Pakiet wymaga `lxml >=5.0,<7` (BSD-3-Clause); libxml2 i libxslt są na licencji
MIT. Szczegóły licencji dołączonych bibliotek mogą zależeć od dystrybucji
`lxml`; oficjalne koła binarne mogą też zawierać m.in. zlib i iconv. Zobacz
[wykaz licencji lxml](https://github.com/lxml/lxml/blob/master/LICENSES.txt).
Do uruchomienia z wcześniej zainstalowanym `lxml` można
zainstalować checkout bez pobierania zależności przez `python -m pip install
--no-deps -e .`.

## API

```python
from pathlib import Path

from render_doc import render_fa3_html

html = render_fa3_html(Path("faktura.xml").read_bytes())
Path("faktura.html").write_text(html, encoding="utf-8")
```

Publiczne API przyjmuje bytes. `InvalidXmlError` oznacza błąd parsowania lub
odrzucony DTD, a `UnsupportedDocumentError` — dokument poza obsługiwanym
profilem. Oba wyjątki oraz bazowy `RenderDocError` są dostępne z `render_doc`.
Parser nie pobiera zewnętrznych encji ani zasobów sieciowych.

## CLI

```sh
render-doc faktura.xml --output faktura.html
```

CLI używa tego samego `render_fa3_html`; odczytuje wyłącznie wskazany lokalny
plik XML i zapisuje HTML jako UTF-8.

## Testy

Testy używają syntetycznego dokumentu i nie potrzebują sieci ani prawdziwych
faktur:

```sh
python -m pytest -q
```

## Źródła i licencje

Mapowanie pól oparto na [oficjalnej broszurze FA(3) Ministerstwa Finansów](https://ksef.podatki.gov.pl/media/jknpcymf/broszura-informacyjna-dotyczaca-struktury-logicznej-fa-3-04032026.pdf).
Oficjalna strona [wzoru FA(3) w CRWDE](https://crd.gov.pl/wzor/2025/06/25/13775/)
udostępnia także odnośnik do `styl.xsl`; jego zawartości, licencji i zachowania
nie zweryfikowano, więc renderer nie używa ani nie kopiuje tego pliku. Projekt
jest na licencji Apache 2.0; jedyną zależnością runtime jest `lxml`.
