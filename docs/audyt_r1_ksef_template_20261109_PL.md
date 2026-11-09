# R1 — raport publikacji szablonu `ksef`

**Data:** 2026-11-09  
**Repozytorium:** `KrzysztofOle/render-doc`, `main`  
**Stan:** **R1_CODE_PUBLISHED / FULL_SUITE_NOT_RUN / MF_PDF_VISUAL_NOT_VERIFIED**.

## Zakres zatwierdzonego kodu

- `src/render_doc/ksef_template.py`: nowy odrębny szablon HTML/CSS do wydruku A4, inspirowany oficjalną wizualizacją MF. Pokazuje kontrahentów, NIP, daty, wiersze, stawki VAT, płatność i dodatkowe opisy.
- `src/render_doc/renderer.py`: publiczne opt-in `render_fa3_html(xml_bytes, template="ksef")`, używające **istniejącego** walidowanego parsera FA(3); nie zmienia wyboru domyślnego ani ścieżki `classic`.
- `src/render_doc/cli.py`: `render-doc faktura.xml --output faktura.html --template ksef`.
- `tests/test_ksef_template.py`: 10 testów jednostkowych szablonu oraz 6 testów integracyjnych API/CLI z istniejącymi przykładami FA(3).
- `README.md`: zakres i ograniczenia nowego opt-in.

## Kontrole wykonane przed publikacją

| Kontrola | Wynik i poziom dowodu |
| --- | --- |
| Zgodność patcha z oryginalnymi plikami GitHub `main` | **PASS**: każdy hunk, kontekst i długość zweryfikowano względem aktualnego źródła; 5/5 plików. |
| `python -m py_compile src/render_doc/ksef_template.py` | **PASS** w izolowanym środowisku poprzedniej sesji. |
| `PYTHONPATH=src python -m pytest -q tests/test_ksef_template.py -k 'not public_api and not cli'` | **10 PASS, 6 deselected** (uruchomione ponownie przed publikacją). |
| `git apply --check`, `git apply`, `git diff --check` | **PASS** na kontrolowanym drzewie fragmentów; **nie** pełny checkout. |
| Chromium: syntetyczny wydruk A4 | **PASS** według poprzedniej sesji; wygenerowano widok ekranowy oraz PDF. |
| Chromium: 75 syntetycznych pozycji | **4 strony**, 75/75 wierszy, powtarzany nagłówek tabeli; podglądy w lokalnym pakiecie R1. |
| Pełne testy starego parsera i nowe 6 integracyjnych | **NIEURUCHOMIONE**: brak kompletnego lokalnego checkoutu przy tej publikacji. |
| Porównanie PDF MF i HTML na tych samych 5 XML | **NOT VERIFIED**; nie deklaruje się pixel-perfect ani wizualnego PASS. |

## Zachowanie i ograniczenia

1. Dotychczasowe `template="default"` i `template="classic"` oraz domyślne wejście pozostają **niezmienione w kodzie**; pełna regresja starych testów nadal wymaga sprawdzenia.
2. Wartość należności pozostaje źródłowym `P_15`; kwota brutto w wierszu stawki jest **pomocniczą** sumą wartości netto i VAT już odczytanych z XML. Żadnego zaokrąglania ani zastępowania `P_15`.
3. HTML nie ładuje skryptów, obcych styli, obrazów ani zasobów sieciowych. Treści XML i opcjonalny numer KSeF są escapowane.
4. **Brak QR i linku weryfikacyjnego**: to etap **R2**, wymagający prawidłowego URL KOD I, środowiska i oryginalnych bajtów XML. R1 nie generuje atrap QR.
5. Nie rozszerzono profilu parsera FA(3), nie dodano PDF do API, nie zmieniono pakietu `ksef-optima-connector`, `KSeF_2` ani `DKF_Html`. Nie wykonywano SQL, operacji na Optimie ani KSeF.
6. Syntetyczne PDF, HTML i PNG z eksperymentu wizualnego są częścią **artefaktów rozmowy** i nie są artefaktami produkcyjnymi biblioteki; do repo wchodzą źródła i odtwarzalne testy, bez osobnych obrazów binarnych.

## Pozostałe kryteria odbioru

- Na pełnym checkoutcie uruchomić `python -m pytest -q`, lint według konfiguracji repo, sprawdzić brak zmian wyników `default/classic` i dostępność CLI `--template ksef`.
- Porównać rzeczywisty PDF oficjalnego [generatora MF](https://github.com/CIRFMF/ksef-pdf-generator) z HTML→PDF `render-doc` na identycznych syntetycznych FA(3) S01–S05. Skorygować wykryte różnice przed deklaracją `VISUAL_PASS`.
- Po pozytywnym QA przystąpić do osobnego R2 (QR KOD I). Nie aktualizować pinu w connectorze ani zgodności z Optimą bez odrębnej weryfikacji i decyzji.

**Podstawa analizy:** [audyt R0](audyt_r0_porownanie_wizualizacji_fa3_mf_20261109_PL.md) i [plan R0–R4](plan_dzia_ania_ksef_xml_do_html_w_python.md).
