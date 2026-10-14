# Plan implementacji render-doc

> **Status:** plan. To repozytorium nie zawiera jeszcze pakietu Python ani
> działającego renderera. Wcześniejsze przykłady kodu były szkicami i nie
> stanowią implementacji, bezpiecznego parsera ani publicznego API.

Docelowy podział odpowiedzialności zatwierdza
[decyzja architektoniczna](architektura_render_doc_i_aplikacji_gui.md).
Ten plan opisuje kolejne możliwe etapy; nie deklaruje ich dostępności.

## Fakty dotyczące źródeł FA(3)

Ministerstwo Finansów publikuje strukturę logiczną FA(3), dokumentację,
broszurę i przykładowe pliki. Nie potwierdzono, aby publikowało oficjalny
arkusz XSLT do tworzenia wizualizacji. Oficjalne repozytorium
[ksef-pdf-generator](https://github.com/CIRFMF/ksef-pdf-generator) generuje
PDF; kod generatora FA(3) tworzy definicję dla `pdfmake` i nie potwierdza
publicznego wyjścia HTML. Nie używać określenia „oficjalny szablon XSLT” bez
konkretnego źródła, licencji i dowodu pochodzenia.

Źródła: [MF — struktura FA(3)](https://ksef.podatki.gov.pl/informacje-ogolne-ksef-20/struktura-logiczna-fa-3/),
[generator PDF MF — README](https://github.com/CIRFMF/ksef-pdf-generator),
[jego kod FA(3)](https://github.com/CIRFMF/ksef-pdf-generator/blob/main/src/lib-public/FA3-generator.ts).

## Etapy

1. **FA(3) XML → HTML:** utworzyć samodzielny pakiet Python i minimalne,
   wersjonowane publiczne API. Ograniczyć pierwszy zakres do jawnie
   wspieranej części FA(3), bezpiecznie przetwarzać XML i generować kompletny
   HTML z lokalnymi zasobami. Nie zakładać XSLT jako techniki ani źródła
   szablonu.
2. **Walidacja publicznego kontraktu:** testy offline na syntetycznych lub
   zanonimizowanych fixture’ach, pokrycie istotnych pól i wariantów,
   sprawdzenie escapowania, odrzuceń, braku dostępu do sieci oraz
   samowystarczalności HTML. Udokumentować ograniczenia obsługi.
3. **FA(3) HTML → PDF:** dodać osobny etap i silnik PDF dopiero po ocenie
   licencji, zależności natywnych, macOS/Windows, trybu offline, paginacji
   i bezpieczeństwa zasobów. API PDF ma korzystać z odpowiedzialności
   render-doc, bez wiązania go z GUI albo konkretnym konsumentem.
4. **Rozszerzenia:** dodawać pozostałe struktury KSeF jako osobne zakresy
   po uzgodnieniu wymagań i testów. Nie deklarować „wszystkich dokumentów
   KSeF” z góry.

## Minimalny etap offline na macOS

Pierwszym zadaniem implementacyjnym powinien być wyłącznie etap 1: minimalny
pakiet i testy publicznego FA(3) → HTML. Weryfikacja nie potrzebuje dostępu
do KSeF ani Optimy. Do czasu wydania i sprawdzenia pakietu konsumenci
pozostają przy istniejących rozwiązaniach. Zgodność HTML z
`CDN.DokumentyKSeF.DKF_Html` wymaga osobnego testu w Optimie i nie wynika
z testów offline.

PDF, GUI, klient KSeF, connector, import kodu z innych repozytoriów oraz
zmiany publicznych API KSeF_2 nie należą do tego etapu.
