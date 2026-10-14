# Plan implementacji render-doc

> **Status:** etap 1 zaimplementowany lokalnie w wersji 0.1.0; kolejne etapy
> pozostają planem. Wcześniejsze fragmenty kodu były szkicami, nie bazą tej
> implementacji.

Docelowy podział odpowiedzialności zatwierdza
[decyzja architektoniczna](architektura_render_doc_i_aplikacji_gui.md).
Ten plan opisuje kolejne możliwe etapy; nie deklaruje ich dostępności.

## Fakty dotyczące źródeł FA(3)

Ministerstwo Finansów publikuje strukturę logiczną FA(3), dokumentację,
broszurę i przykładowe pliki. Strona wzoru FA(3) w CRWDE zawiera odnośnik do
`styl.xsl`; w tym etapie nie używamy ani nie kopiujemy tego pliku, ponieważ
nie sprawdzono jego zawartości, warunków licencji, bezpieczeństwa ani
przydatności jako samodzielnego HTML dla różnych aplikacji. Oficjalne repozytorium
[ksef-pdf-generator](https://github.com/CIRFMF/ksef-pdf-generator) generuje
PDF; kod generatora FA(3) tworzy definicję dla `pdfmake` i nie potwierdza
publicznego wyjścia HTML. Nie używać XSLT bez uprzedniej weryfikacji źródła,
licencji, zawartości i zachowania offline.

Źródła: [MF — struktura FA(3)](https://ksef.podatki.gov.pl/informacje-ogolne-ksef-20/struktura-logiczna-fa-3/),
[wzór FA(3) w CRWDE](https://crd.gov.pl/wzor/2025/06/25/13775/),
[generator PDF MF — README](https://github.com/CIRFMF/ksef-pdf-generator),
[jego kod FA(3)](https://github.com/CIRFMF/ksef-pdf-generator/blob/main/src/lib-public/FA3-generator.ts).

## Etapy

1. **FA(3) XML → HTML — zaimplementowany profil początkowy:** pakiet Python,
   publiczne API i CLI renderują ograniczoną podstawową fakturę FA(3) PLN/VAT
   23 do kompletnego HTML. Pełna walidacja XSD i pozostałe warianty FA(3) nie
   są obsługiwane; szczegóły podano w README.
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

Etap 1 działa lokalnie na macOS i jego testy nie potrzebują dostępu do KSeF
ani Optimy. Do czasu wydania i sprawdzenia pakietu konsumenci pozostają przy
istniejących rozwiązaniach. Zgodność HTML z
`CDN.DokumentyKSeF.DKF_Html` wymaga osobnego testu w Optimie i nie wynika
z testów offline.

PDF, GUI, klient KSeF, connector, import kodu z innych repozytoriów oraz
zmiany publicznych API KSeF_2 nie należą do tego etapu.
