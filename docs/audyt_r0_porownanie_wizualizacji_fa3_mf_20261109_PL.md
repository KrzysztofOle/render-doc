# R0 — audyt referencji wizualnej FA(3) względem generatora PDF MF

**Data:** 2026-11-09  
**Status:** `R0_SOURCE_REVIEW_COMPLETE / VISUAL_PDF_NOT_VERIFIED`  
**Zakres:** analiza istniejących szablonów `default` i `classic`, pięciu syntetycznych par XML/HTML oraz kodu referencyjnego generatora PDF MF; bez zmian aplikacji, API, testów i zależności.  
**Repozytoria i zamrożone odczyty:**
- `KrzysztofOle/render-doc`, `main` @ `07f508e8d5cbb6733b78c24805c1c3a71bd205c8`;
- `CIRFMF/ksef-pdf-generator`, `main` @ `d766b7b79486ed401cd40fac27402ffecd672bd7`;
- `KrzysztofOle/ksef-optima-connector`, `main` @ `9d7df3a6bdd6800efa80f8c06089ffd334e4c4c0` (stan integracji na wejściu do R0).

## 1. Metoda i jakość dowodu

1. Sprawdzono bieżące `AGENTS.md` (`render-doc`: pusty), `README.md`, `pyproject.toml`, `src/render_doc/renderer.py`, publiczne API, CLI, testy oraz **wszystkie pięć** istniejących syntetycznych przykładów `docs/examples/classic/*.{xml,html}`.
2. Porównano strukturę dokumentu i warunki renderowania z aktualnym kodem Ministerstwa Finansów/CIRF: `FA3-generator.ts`, `common/Naglowek.ts`, `FA3/Podmioty.ts`, `FA3/Szczegoly.ts`, `FA3/Wiersze.ts`, `FA3/PodsumowanieStawekPodatkuVat.ts`, `FA3/Platnosc.ts`, `common/Stopka.ts`, `shared/PDF-functions.ts` i `AdditionalDataTypes`.
3. Przeprowadzono **statyczną kontrolę treści** pięciu par XML/HTML (numery, stawki i liczby pozycji, obecność sekcji płatności, QR, linku, reguły A4). Nie wykonywano nowego generatora HTML; przykłady są wersjonowanymi wynikami wcześniejszego renderowania.
4. **Ograniczenie krytyczne dla interpretacji:** nie uzyskano w tej sesji PDF generowanego przez oficjalny silnik MF **z identycznego XML** ani zrzutów przeglądarkowych bieżących pięciu HTML. Nie wykonywano pomiaru pozycji pikseli, typografii ani różnic obrazowych. Zestawienie porównuje **implementację i zawartość wyników**, nie rozstrzyga zgodności graficznej. Nie deklarować `VISUAL_PASS` ani `R0_FULL_VISUAL_COMPLETE`.

**Konkluzja:** R0 dostarczył inwentaryzację, macierz różnic, trzy istniejące podglądy referencyjne oraz wymaganą specyfikację R1. Element wymagający rzeczywistego porównania PDF ↔ HTML pozostaje `NOT_VERIFIED` i powinien zostać wykonany **przed zatwierdzeniem wizualnego odbioru R1**, na identycznych syntetycznych XML.

## 2. Zbadane przypadki

| Przypadek | Dokument | Dane wejściowe | Obserwacja w wersjonowanym HTML classic |
|---|---|---|---|
| S01 | [01 XML](examples/classic/01-jedna-pozycja-vat-23.xml) / [01 HTML](examples/classic/01-jedna-pozycja-vat-23.html) | `SYN/2026/001`, 1 pozycja, VAT 23% | Tabela, suma VAT, NIP, kwota do zapłaty, dodatkowe opisy i numer KSeF; brak QR/linku |
| S02 | [02 XML](examples/classic/02-mieszane-stawki-vat.xml) / [02 HTML](examples/classic/02-mieszane-stawki-vat.html) | `SYN/2026/002`, 2 pozycje, VAT 23% i 8% | Dwie stawki i zestawienie VAT; brak QR/linku |
| S03 | [03 XML](examples/classic/03-wiele-pozycji-dlugie-opisy-i-nazwy.xml) / [03 HTML](examples/classic/03-wiele-pozycji-dlugie-opisy-i-nazwy.html) | `SYN/2026/003`, 3 pozycje, wydłużone nazwy/opisy, VAT 23% | Dłuższe treści obecne; **brak dowodu** na poprawną paginację przy kilkudziesięciu pozycjach; brak QR/linku |
| S04 | [04 XML](examples/classic/04-przelew-termin-rachunek.xml) / [04 HTML](examples/classic/04-przelew-termin-rachunek.html) | `SYN/2026/004`, 1 pozycja, termin, forma przelew i rachunek | Sekcja płatności i banku obecna; brak QR/linku |
| S05 | [05 XML](examples/classic/05-warianty-vat-zero.xml) / [05 HTML](examples/classic/05-warianty-vat-zero.html) | `SYN/2026/005`, 3 pozycje, `0 KR`, `0 WDT`, `0 EX` | Rozróżnienia stawek 0% istnieją; brak QR/linku |

Kontrola statyczna: **5/5** HTML zawiera `@page { size: A4; ... }` oraz identyfikację numeru KSeF; **0/5** zawiera osadzony obraz QR lub odnośnik `href`. Nie są to żywe faktury KSeF: syntetyczne numery i NIP-y nie nadają się na działające linki weryfikacyjne.

**Trzy istniejące podglądy, stanowiące bazę R1** (bez dodawania duplikatów): [S01 — podstawowa](examples/classic/01-jedna-pozycja-vat-23.html), [S03 — długie opisy](examples/classic/03-wiele-pozycji-dlugie-opisy-i-nazwy.html), [S04 — płatność i rachunek](examples/classic/04-przelew-termin-rachunek.html). To podglądy HTML wersjonowane w repozytorium, **nie** nowo wykonane screenshoty ani oficjalne PDF.

## 3. Macierz różnic `default` / `classic` / MF

| ID | Obszar | `default` | `classic` | MF — ustalenie na podstawie kodu | Priorytet i zadanie R1/R2 |
|---|---|---|---|---|---|
| V01 | Nagłówek | „Faktura” i numer w opisie po lewej | „Faktura [P_2]” po lewej | Odrębny trzyczęściowy znak `KSeF` (18 pt, czerwony akcent) oraz numer faktury, rodzaj faktury i numer KSeF wyrównane do prawej | **P0/R1:** oddzielny nagłówek `ksef` |
| V02 | Dane stron | Dwie sekcje CSS grid | Dwie komórki tabeli z nazwą, NIP i adresem | Podstawowe strony w dwóch kolumnach, rozdzielanych odstępem 20 (pdfmake), dodatkowe warianty stron | **P1/R1:** przybliżyć hierarchię etykiet i odstępy; zachować zakres danych parsera |
| V03 | Daty i szczegóły | `P_1`, opcjonalnie `P_6` jako ISO | `P_1`, `P_6` jako ISO w tabeli | Dedykowana sekcja szczegółów, data wydruku formatowana na PL, opcjonalne miejsce wystawienia/kursy i okresy | **P1/R1:** układ i format dat; nie akceptować nieobsługiwanych źródeł pól |
| V04 | Pozycje | Stałe 6 kolumn | Stałe 6 kolumn (ilość i jednostka razem) | Dynamiczne kolumny zależne od pól; m.in. osobna jednostka, ilość, rabat, dodatkowe ceny/identyfikatory | **P1/R1:** dopasować kolumny dla wspieranego profilu, czytelność i paginację; poszerzenie parsera osobno |
| V05 | Zestawienie VAT | Wiersze jako `div` netto i VAT | Tabela netto i VAT | Tabela z pozycją, stawką, netto, VAT, **brutto** oraz warunkowym VAT PLN | **P0/R1:** tabela netto/VAT/brutto, bez samowolnych przeliczeń; pochodzenie brutto jawnie udokumentować |
| V06 | Kwota do zapłaty | Podsumowanie bez mocnego wyróżnienia rachunkowego | Wyraźny pasek `Do zapłaty`, liczby formatowane PL | Mocno wyróżniona należność w sekcji pozycji, po prawej | **P0/R1:** zachować `P_15` jako dane źródłowe, dopasować hierarchię |
| V07 | Płatność | Opis tekstowy terminu/formy/konta | Tabela etykiet i wartości | Osobna sekcja `Platnosc` z rozbudowanymi tabelami i opcjami | **P1/R1:** układ dla istniejącego profilu; nie rozszerzać wariantów bez mapowania |
| V08 | Adnotacje / dodatki | Obsługa wybranych zwalidowanych opisów | Obsługa wybranych zwalidowanych opisów | Oddzielne sekcje adnotacji i informacji dodatkowych | **P1/R1:** semantyczny przegląd istniejącego zakresu, bez pomijania aktywnych znaczników |
| V09 | QR KOD I | Brak | Brak | `common/Stopka.ts`: na podstawie `additionalData.qrCode` drukuje QR wielkości `150` (jednostki pdfmake), etykietę numeru KSeF lub `OFFLINE`, opis i klikalny URL obok | **P0/R2:** prawidłowy QR/URL i etykieta; renderer MF **otrzymuje** URL, a nie wyprowadza go z XML |
| V10 | QR KOD II | Brak | Brak | Osobny `qr2Code` i etykieta `CERTYFIKAT`; rozmiar `210` (pdfmake) | **Poza MVP** — certyfikat/podpis osobna decyzja |
| V11 | Druk | Responsywny CSS, brak jawnego `@page` | `@page A4; margin: 12mm`, print media | PDF z `generateStyle` oraz stopką numerującą strony `n / total` | **P1/R1:** A4, stopka i łamanie długich tabel; **niezweryfikowane obrazowo** |
| V12 | Barwy / typografia | Granatowe nagłówki, ramki sekcji | Minimalistyczna czerń/szarości, tabele | Szarości `#343A40`, `#F6F7FA`, czerwień w znaku KSeF; rozmiary 18/16/10/9/7 pt zależnie od roli | **P1/R1:** tokeny wyglądu oparte na MF, bez kopiowania zależności i bez deklaracji pixel-perfect |
| V13 | Zgodność z Optimą | Niepotwierdzona | Niepotwierdzona | PDF MF nie jest kontraktem `DKF_Html` Optimy | **Odrębny R3:** nie zmieniać stanu `unsupported` i nie wykonywać SQL |

**Uwaga o treści:** `default` i `classic` korzystają z tego samego ograniczonego parsera FA(3); różnica wyglądu nie jest dowodem obsługi dodatkowych pól. `classic` rozdziela nazwę i NIP przez parsowanie sklejonego tekstu `" (NIP: ... )"`; w R1 warto oprzeć nowe widoki na jednoznacznym modelu, ale bez pobocznego refaktoringu w R0.

## 4. Minimalna specyfikacja wizualna R1 — szablon `ksef`

**Cel R1:** wizualnie *zbliżony* do PDF MF, czytelny w przeglądarce i przy wydruku A4; nie deklarować identyczności 1:1 przed rzeczywistym porównaniem. Wykorzystać obecny parser, obecną walidację i CSS `classic`; pozostawić wyniki `default`/`classic` bez zmian.

**Kolejność i hierarchia A4:**
1. Góra: widoczny, odróżniający się znak `KSeF` w stylu MF; po prawej numer faktury `P_2`, rodzaj dokumentu i opcjonalny numer KSeF.
2. Strony transakcji: sprzedawca i nabywca obok siebie, podpisane etykietami, z **osobnym** NIP i adresem; zawijanie nazw bez nachodzenia.
3. Szczegóły: osobno data wystawienia `P_1` i data wykonania/dostawy `P_6`, jeśli obecna; jawny podpis znaczenia pola.
4. Pozycje: wyraźne nagłówki tabeli; liczby do prawej, tekst do lewej; kolumny dopasowane do obsługiwanych pól; bez uciania długich opisów. Przy wielu stronach nagłówek tabeli powinien pozostać czytelny.
5. Podsumowanie stawek: tabela stawka/netto/VAT/brutto **tylko gdy składniki brutto można uzasadnić bez nadpisania źródłowych wartości**; suma do zapłaty z `P_15`, wyróżniona i nieprzeliczana.
6. Płatność: termin, forma, rachunek, tylko gdy obecne; dodatkowe informacje, tylko gdy obsługiwane i zwalidowane.
7. Panel weryfikacji: **rezerwa miejsca** na jeden KOD I, etykietę i link. **W R1 nie tworzyć atrap QR i nie oznaczać dokumentu jako zweryfikowany**; R2 odpowiada za prawdziwe dane URL/QR.
8. Stopka: liczba stron, bez sugerowania oficjalnego podpisu MF; wersjonować wygląd wyłącznie opt-in.

**Testy odbiorowe R1 po uzyskaniu środowiska wizualnego:**
- Ten sam **oryginalny syntetyczny XML** w generatorze MF i w `render-doc`, z jednoznacznym środowiskiem/metadanymi (QR pominięty, jeśli brak legalnie wytworzonego URL).
- Przynajmniej S01, S02, S03, S04, S05: PDF MF (referencja) vs HTML→druk A4 (kandydat); screenshots stron i checklist: nagłówek, daty, NIP, pozycje, VAT, należność, płatność, dodatkowe opisy.
- Osobny **nowy syntetyczny test wielostronicowy** z dostateczną liczbą wierszy; S03 (3 wiersze) nie wystarcza do testu paginacji.
- Weryfikacja zrzutów na rzeczywistym silniku renderującym; jeśli PDF MF nie może zostać wygenerowany, nie oznaczać wyniku graficznego jako PASS.
- Bez poszerzenia parsera i bez naruszania `default`/`classic`. R1 dopuszczony do realizacji dopiero po decyzji o nowym publicznym `template="ksef"`; nie zakładać samodzielnej akceptacji API.

## 5. Źródła i rozgraniczenie odpowiedzialności

- `render-doc`: [renderer](../src/render_doc/renderer.py), [API](../src/render_doc/__init__.py), [CLI](../src/render_doc/cli.py), [testy](../tests/test_renderer.py), [5 przykładów](examples/classic/index.html), [plan R0–R4](plan_dzia_ania_ksef_xml_do_html_w_python.md).
- MF/CIRF: [FA3-generator.ts](https://github.com/CIRFMF/ksef-pdf-generator/blob/main/src/lib-public/FA3-generator.ts), [Naglowek.ts](https://github.com/CIRFMF/ksef-pdf-generator/blob/main/src/lib-public/generators/common/Naglowek.ts), [Wiersze.ts](https://github.com/CIRFMF/ksef-pdf-generator/blob/main/src/lib-public/generators/FA3/Wiersze.ts), [PodsumowanieStawekPodatkuVat.ts](https://github.com/CIRFMF/ksef-pdf-generator/blob/main/src/lib-public/generators/FA3/PodsumowanieStawekPodatkuVat.ts), [Stopka.ts](https://github.com/CIRFMF/ksef-pdf-generator/blob/main/src/lib-public/generators/common/Stopka.ts), [PDF-functions.ts](https://github.com/CIRFMF/ksef-pdf-generator/blob/main/src/shared/PDF-functions.ts); licencja biblioteki MIT.
- [Wytyczne KSeF QR](https://github.com/CIRFMF/ksef-api/blob/main/kody-qr.md). **QR w R2**, nie w R0. Podstawa linku, źródłowe bajty XML, środowisko TEST/DEMO/PROD i pochodzenie numeru to osobny kontrakt.
- `ksef-optima-connector`: [adapter](https://github.com/KrzysztofOle/ksef-optima-connector/blob/main/src/ksef_optima/invoice_renderer.py) domyślnie używa `default`; [DKF mapper](https://github.com/KrzysztofOle/ksef-optima-connector/blob/main/src/ksef_optima/dkf_mapper.py) nie uznaje `DKF_Html` za kompatybilny. Nie zmieniano tych plików.

## 6. Wynik i kolejne wejście

- **PASS:** istniejące możliwości zidentyfikowane, nie dodano duplikatów; 5/5 syntetycznych HTML/XML przeanalizowano statycznie; macierz 13 różnic i specyfikacja A4 gotowe.
- **NOT VERIFIED:** rzeczywiste PDF MF z tych samych XML, zrzuty z przeglądarki, porównanie pixel/layout, druk wielostronicowy. To nie jest regresja ani dowód działania oficjalnego generatora na tych danych.
- **R1:** preferowany osobny szablon `ksef` w istniejącej bibliotece; mały etap wyłącznie wizualny, bez kodu QR, PDF, rozszerzania FA(3) i bez integracji SQL.
- **R2:** prawdziwy QR KOD I z lokalnym URL na podstawie autentycznych danych wejściowych; bez KODU II i sekretów.
- **Weryfikacja samego raportu:** dokumentacja R0, testów aplikacji nie uruchamiano; repozytoria i pliki źródłowe odczytano przez GitHub, bez pracy na bazie danych lub KSeF.
