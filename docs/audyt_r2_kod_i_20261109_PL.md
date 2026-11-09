# R2 — KSeF KOD I: implementacja i weryfikacja

**Data:** 2026-11-09  
**Repozytorium:** KrzysztofOle/render-doc, main  
**Status:** R2_CODE_PUBLISHED / TARGETED_QA_PASS / FULL_SUITE_NOT_RUN.  
**Źródło normatywne:** [CIRF/MF — kody weryfikujące QR](https://github.com/CIRFMF/ksef-api/blob/main/kody-qr.md), odczyt 2026-11-09; generator PDF MF [Stopka.ts](https://github.com/CIRFMF/ksef-pdf-generator/blob/main/src/lib-public/generators/common/Stopka.ts).

## Co wdrożono

- Publiczna metadana \`KsefVerification(environment, ksef_number)\` (test, demo, prod), jedynie jako jawna deklaracja wywołującego. Renderer **nie kontaktuje się z KSeF** i nie potwierdza autentyczności.
- Opcjonalny argument \`verification\` w \`render_fa3_html(..., template="ksef")\`, bez modyfikacji starego wyjścia \`default\` i \`classic\`.
- KOD I: URL \`/invoice/<NIP sprzedawcy>/<P_1 DD-MM-RRRR>/<SHA-256 oryginalnych bajtów XML Base64URL bez paddingu>\`, host odpowiedni do TEST/DEMO/PROD; użyty ten sam URL w QR i klikalnym linku.
- Offline PNG QR w \`data:image/png;base64\` bez zewnętrznych zasobów; pod QR numer KSeF, obok jawny link i komunikat o braku gwarancji autentyczności; TEST i DEMO oznaczone jako dokument demonstracyjny.
- Samowystarczalny CSS do druku A4 oraz CLI z \`--template ksef --qr-environment DEMO --ksef-number ...\`.
- Dodana zależność \`qrcode[pil]>=8,<9\`, Pillow użyte do PNG. Bez certyfikatów, KOD II, sekretów i SQL.

## Zakres dowodów

| Kontrola | Wynik |
|---|---|
| Testy jednostkowe R2, w tym TEST/DEMO/PROD, hash bajtów i negatywne przypadki | PASS w izolowanym środowisku źródła (17 testów przed rozdzieleniem skanowania, następnie 18 po rozdzieleniu). |
| Łączna regresja testów celowanych R1 + R2 | **28 PASS**, **6 deselected** (są to dotychczasowe testy integracyjne R1 wymagające pełnego checkoutu). |
| Parser/CLI w pełnym checkoutcie, nowe testy API i CLI R2 | **NIEWYKONANE**; repozytorium jest dostępne przez konektor GitHub, bez kompletnego lokalnego klonu. Testy integracyjne dodano do \`tests/test_ksef_verification.py\`, lecz ich wyniku nie przedstawia się jako PASS. |
| PNG QR skanowane OpenCV | **PASS**, odczyt dokładnie zgodny z \`href\` i wektorem URL (dane w całości syntetyczne). |
| Chromium HTML → PDF A4, pojedyncza syntetyczna faktura | **PASS: 1 strona** po poprawie stopki; QR odczytany również ze skanu obrazu strony PDF. |
| Zewnętrzne żądania podczas generowania QR | **0** (test z zablokowanym \`socket.connect\`). |
| Rozbieżność bajtów wejścia XML przy semantycznie podobnym XML | **PASS**: zmiana spacji zmienia SHA-256 URL; brak normalizacji. |
| Generator PDF MF 1:1 i GUI Optimy | **NIEZWERYFIKOWANE**; osobne kryteria QA/R3. |

Testowana lokalnie konfiguracja: Python 3.13, \`qrcode 8.2\`, \`Pillow 12.3.0\`, \`lxml 6.1.1\`, \`pytest 9.0.2\`, Chromium i opcjonalnie OpenCV do skanowania.

## Gwarancje i ograniczenia

1. **Nie wolno** generować „potwierdzonego” QR na podstawie samego numeru wpisanego przez użytkownika. To wywołujący musi zweryfikować jego pochodzenie z odbioru KSeF; dataclass nie może kryptograficznie dowieść pochodzenia. Sam link i QR nie potwierdzają przyjęcia faktury.
2. W R3 connector powinien przekazać **te same oryginalne bajty FA(3)**, na których KSeF wyliczył hash. Dziś connector przyjmuje \`raw_xml: str\`, co może zniekształcić bajtową tożsamość. Bez dowodu nie włączać QR produkcyjnie. Przed integracją uzgodnić publiczny kontrakt i pochodzenie numeru.
3. KOD II wymaga certyfikatu offline i podpisu; nie jest objęty R2. Brak zapytań do serwera KSeF, bez zewnętrznej walidacji ani weryfikacji numerów.
4. Wydruk HTML jest oddzielny od formatu \`DKF_Html\` Optimy, który pozostaje w connectorze **unsupported**. R2 nie dotyka Optimy, SQL ani \`KSeF_2\`.
5. Nie zmieniano logiki parsera FA(3), szablonów \`default\`/\`classic\` i nie publikowano wersji, tagu ani Release.
6. Bez uzgodnienia nie aktualizować pinu \`render-doc\` w connectorze.

## Po publikacji

- Odczyt HEAD oraz diffu GitHub w celu potwierdzenia zakresu zmian.
- Uruchomić pełne \`python -m pytest -q\` w repo oraz kontrolę CLI; wymagane również porównanie z oficjalnym PDF MF, zanim R1 zostanie uznane za pełną zgodność wizualną.
- **Następny krok funkcjonalny R3** dopiero po decyzji o granicy API i dowodzie oryginalnych bajtów XML; bez SQL DML/Optima write.

