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

Repozytorium render-doc zawiera obecnie dokumentację, a nie pakiet ani gotowy
renderer. Przykładowe fragmenty kodu z wcześniejszych dokumentów nie są
implementacją ani zatwierdzonym kontraktem API.

KSeF_2 zachowuje obecny renderer `ksef_invoice_renderer`, jego zachowanie
i publiczne API w okresie przejściowym. Connector zachowuje istniejący
adapter do tego API bez zmian, aż render-doc będzie dostępny i zweryfikowany.
Następnie odbiorcy mogą migrować niezależnie. Oznaczenie API KSeF_2 jako
deprecated wymaga osobnej decyzji; usunięcie wymaga osobnej decyzji i wydania
głównego zgodnego z SemVer. Ta decyzja nie wprowadza deprecacji ani usunięcia.

Connector utrzymuje `DKF_Html = unsupported`, dopóki zgodność wyniku
render-doc z Optimą nie zostanie potwierdzona w dopuszczonym badaniu.

## Założenia nienormatywne i otwarte decyzje

- Nie zakłada się dostępności oficjalnego XSLT MF do wizualizacji. MF
  publikuje strukturę FA(3), dokumentację i przykładowe pliki; wskazany
  oficjalny generator PDF buduje dokument przez `pdfmake`, co samo w sobie
  nie udostępnia HTML. Zob. [strona MF o FA(3)](https://ksef.podatki.gov.pl/informacje-ogolne-ksef-20/struktura-logiczna-fa-3/),
  [repozytorium generatora PDF MF](https://github.com/CIRFMF/ksef-pdf-generator)
  i [kod generatora FA3](https://github.com/CIRFMF/ksef-pdf-generator/blob/main/src/lib-public/FA3-generator.ts).
- Wybór parsera, formatu publicznego API, szablonu HTML i silnika PDF pozostaje
  do rozstrzygnięcia przy implementacji. Wybór bibliotek lub szablonów wymaga
  osobnej weryfikacji ich licencji, pochodzenia i przenośności.
- Zakres wariantów FA(3), lokalizacje, branding i dalsze formaty będą
  rozszerzane na podstawie osobnych wymagań; nie są uznane za obsługiwane.
- API, pakietowanie i polityka wersji wymagają konkretnej specyfikacji przed
  pierwszym wydaniem. Ta decyzja zatwierdza właściciela i kierunek, nie
  szczegóły API.

## Najmniejszy pierwszy etap implementacji

W osobnym zadaniu utworzyć minimalny pakiet instalowalny i jedną publiczną,
wersjonowaną operację FA(3) XML → kompletny HTML. Użyć lokalnego,
zanonimizowanego lub syntetycznego fixture; wygenerowany dokument ma zawierać
osadzony CSS i nie wymagać sieci. Dodać testy offline dla poprawnego wejścia,
wartości faktury, bezpiecznego odrzucenia nieobsługiwanych danych i braku
zewnętrznych zasobów. Etap nie obejmuje PDF, GUI, KSeF, Optimy ani migracji
klientów. Można go wykonać na macOS bez połączeń sieciowych po przygotowaniu
środowiska i fixture.

**Zakres tego dokumentu:** utrwalenie zatwierdzonego podziału odpowiedzialności;
nie stwierdza zaimplementowania pakietu ani żadnej z planowanych capabilities.
