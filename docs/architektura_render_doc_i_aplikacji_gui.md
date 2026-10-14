# Decyzja architektoniczna: render-doc jako właściciel wizualizacji KSeF

- **Status:** zaakceptowana
- **Data:** 2026-10-14

## Kontekst

Wizualizacja XML KSeF jest wspólną funkcją prezentacyjną, która ma być
wykorzystywana przez niezależne aplikacje. Nie należy do komunikacji z KSeF
ani do integracji z konkretnym ERP. Dotychczasowe dokumenty render-doc
zakładały istnienie oficjalnych arkuszy XSLT MF, choć projekt nie zawiera
implementacji ani takich szablonów.

## Decyzja

Repozytorium `render-doc` jest docelowym właścicielem samodzielnego pakietu
Python do lokalnego, offline renderowania dokumentów KSeF. Pakiet ma mieć
wersjonowane publiczne API, przyjmować lokalny XML i docelowo zwracać HTML
oraz PDF. Pierwszym obsługiwanym formatem jest FA(3) XML → HTML; PDF i kolejne
struktury dokumentów są późniejszymi etapami.

Pakiet pozostaje niezależny od KSeF_2, Comarch ERP Optima i connectora. HTML
ma być kompletnym, samowystarczalnym dokumentem do wykorzystania przez różne
aplikacje. Zgodność z `CDN.DokumentyKSeF.DKF_Html` nie wynika z samego faktu,
że wynik jest poprawnym HTML; wymaga osobnego potwierdzenia w Optimie.

## Podział odpowiedzialności

```text
KSeF_2
  └─ komunikacja z KSeF; udostępnia oryginalny dokument XML

render-doc
  └─ niezależne, lokalne renderowanie XML do HTML i PDF

ksef-optima-connector
  ├─ pobieranie i synchronizacja dokumentów przez publiczne API KSeF_2
  ├─ mapowanie danych i projekcja rekordów DKF
  ├─ wykorzystanie render-doc jako docelowego źródła HTML/PDF
  └─ zgodność DKF_Html, integracja SQL i jej bezpieczeństwo
```

Żaden projekt nie wprowadza zależności cyklicznej. `render-doc` nie importuje
KSeF_2 ani connectora. KSeF_2 nie zależy od render-doc. Connector przekazuje
XML do rendererów jako klient, po ich wydaniu i osobnym wdrożeniu.

## Stan obecny i migracja

Repozytorium zawiera pakiet Python `render-doc` 0.1.0 z publicznym API
`render_fa3_html(xml_bytes: bytes) -> str` oraz CLI `render-doc`. Pierwsza
implementacja renderuje do samowystarczalnego HTML ograniczony profil
podstawowej faktury FA(3): PLN, stawka 23%, pojedyncze nazwy/NIP stron i
podstawowe pozycje oraz sumy. To nie jest pełna walidacja XSD ani pełna obsługa
FA(3); zakres i odrzucane warianty opisuje README. Nie potwierdzono zgodności
HTML z Optimą.

KSeF_2 zachowuje obecny renderer `ksef_invoice_renderer`, jego zachowanie
i publiczne API w okresie przejściowym. Connector zachowuje istniejący
adapter do tego API bez zmian, aż render-doc będzie dostępny i zweryfikowany.
Następnie odbiorcy mogą migrować niezależnie. Oznaczenie API KSeF_2 jako
deprecated wymaga osobnej decyzji; usunięcie wymaga osobnej decyzji i wydania
głównego zgodnego z SemVer. Ta decyzja nie wprowadza deprecacji ani usunięcia.

Connector utrzymuje `DKF_Html = unsupported`, dopóki zgodność wyniku
render-doc z Optimą nie zostanie potwierdzona w dopuszczonym badaniu.

## Założenia nienormatywne i otwarte decyzje

- Oficjalna strona wzoru FA(3) w CRWDE udostępnia odnośnik do pliku
  `styl.xsl`. Samo istnienie pliku nie potwierdza jego zakresu, licencji,
  bezpieczeństwa ani tego, że jest właściwym kontraktem HTML dla różnych
  aplikacji; nie jest używany w pierwszym etapie bez osobnego sprawdzenia.
  Wskazany generator PDF MF buduje dokument przez `pdfmake`, co samo w sobie
  nie udostępnia HTML. Zob. [strona MF o FA(3)](https://ksef.podatki.gov.pl/informacje-ogolne-ksef-20/struktura-logiczna-fa-3/),
  [wzór FA(3) w CRWDE](https://crd.gov.pl/wzor/2025/06/25/13775/),
  [repozytorium generatora PDF MF](https://github.com/CIRFMF/ksef-pdf-generator)
  i [kod generatora FA3](https://github.com/CIRFMF/ksef-pdf-generator/blob/main/src/lib-public/FA3-generator.ts).
- Pierwszy etap używa `lxml`, publicznego API `render_fa3_html` i osadzonego
  CSS. Integracja z `styl.xsl` nie została zatwierdzona. Wybór silnika PDF
  i ewentualna zmiana zakresu API wymagają osobnego etapu oraz sprawdzenia
  licencji, pochodzenia, przenośności i bezpieczeństwa.
- Zakres wariantów FA(3), lokalizacje, branding i dalsze formaty będą
  rozszerzane na podstawie osobnych wymagań; nie są uznane za obsługiwane.
- Wersja 0.1.0 jest pierwszą lokalną implementacją; polityka wydań i dalsza
  stabilizacja API pozostają do ustalenia przed publikacją pakietu.

## Najmniejszy pierwszy etap implementacji

Etap 1 został zaimplementowany jako lokalny pakiet instalowalny 0.1.0 z API
FA(3) XML → kompletny HTML i CLI. Testy używają syntetycznego fixture oraz
sprawdzają parser, renderowanie, CLI, brak zewnętrznych zasobów i brak
połączeń sieciowych. Etap nie obejmuje PDF, GUI, KSeF, Optimy ani migracji
klientów. Zgodność `DKF_Html` nadal wymaga osobnego potwierdzenia w Optimie.

**Zakres tego dokumentu:** utrwalenie podziału odpowiedzialności i wskazanie
stanu pierwszego lokalnego etapu; nie oznacza publikacji pakietu ani zgodności
HTML z Optimą.
