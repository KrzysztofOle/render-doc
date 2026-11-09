# Plan rozwoju `render-doc`: wizualizacja FA(3) jak w KSeF, QR i integracja z Optimą

> **Status:** R0 zweryfikowany źródłowo; R1 zaimplementowany w opt-in, pełna regresja i porównanie MF pending; R2–R4 niezaimplementowane — 2026-11-09.  
> **Repozytorium:** `KrzysztofOle/render-doc`, gałąź `main`.  
> **Cel:** czytelna wizualizacja faktury FA(3) możliwie zbliżona do wizualizacji MF/KSeF, zawierająca prawidłowy QR i link weryfikacyjny, do wykorzystania przez `ksef-optima-connector`.  
> **Granice:** ten dokument nie wdraża kodu, nie publikuje wydania i nie daje zgody na SQL DML, import do Optimy, operacje KSeF ani użycie sekretów.

## Status R0 — audyt wykonany 2026-11-09

**R0_SOURCE_REVIEW_COMPLETE / VISUAL_PDF_NOT_VERIFIED.** Dokonano odczytowej analizy 5/5 istniejących par syntetycznych FA(3) XML/HTML, obu szablonów `default`/`classic` i kodu oficjalnego generatora PDF MF. Zapisano macierz 13 różnic, specyfikację A4 dla R1 i trzy referencyjne istniejące podglądy HTML. **Brak w tej sesji uruchomionego generatora PDF MF na tych samych XML oraz porównania obrazu A4; nie deklarować wizualnego PASS.** Szczegóły i źródła: [audyt R0](audyt_r0_porownanie_wizualizacji_fa3_mf_20261109_PL.md).

Kolejne ograniczone zadanie to **R1 — opt-in szablon `ksef`**, po zatwierdzeniu zmiany publicznego API. Rzeczywiste porównanie PDF ↔ HTML na identycznych syntetycznych dokumentach jest obowiązkowym kryterium odbioru wizualnego R1. R2 (prawidłowy QR) pozostaje osobnym etapem.

## Status R1 — implementacja 2026-11-09

**R1_CODE_PUBLISHED / FULL_SUITE_NOT_RUN / MF_PDF_VISUAL_NOT_VERIFIED.** Dodano opt-in `template="ksef"` do publicznego API i CLI, samowystarczalny szablon HTML/CSS A4 oraz 16 testów (10 jednostkowych wykonano z PASS; 6 integracyjnych oczekuje na pełny checkout). `default` i `classic` nie zostały zmienione. Chromium potwierdził demonstracyjny wydruk 1- i 4-stronicowy, ale **brak** bezpośredniego porównania PDF MF ↔ HTML na tych samych XML. QR nie wchodzi w R1. Raport i kryteria domknięcia: [R1 QA](audyt_r1_ksef_template_20261109_PL.md).

## 1. Stan potwierdzony na 2026-11-09

| Obszar | Fakty |
| --- | --- |
| `render-doc/main` | `f9cbe7624969754f920a0cb091bf1a10dfff2086`, dystrybucja `0.2.0` |
| `ksef-optima-connector/main` | `9d7df3a6bdd6800efa80f8c06089ffd334e4c4c0`; `pyproject.toml` przypina **dokładnie** powyższy commit render-doc |
| Publiczne API | `render_doc.render_fa3_html(xml_bytes, *, ksef_number=None, template="default") -> str` |
| Szablony | `default` oraz `classic` (zwięzły, księgowy; 5 syntetycznych przykładów w `docs/examples/classic/`) |
| Pokrycie | ścisły **ograniczony** profil FA(3) VAT/PLN: podstawowe dane, strony, pozycje, stawki 23/8/5/0/zw, część pól płatności/adnotacji; nie jest pełnym rendererem FA(3) |
| Brak | QR i linków weryfikacyjnych, PDF, obsługi korekt/zaliczek i wielu wariantów FA(3) |
| Connector | `src/ksef_optima/invoice_renderer.py` wywołuje publiczne API z XML i numerem KSeF, **bez** `template="classic"`, więc używa `default` |
| Projekcja DKF | `DkfProjector` przekazuje HTML do `DKFMapper`; `DKF_Html` ma nadal stan **unsupported**, mimo że lokalne bajty mogą zostać wygenerowane. Zgodność z Optimą i ewentualne zapisy to **oddzielna sprawa**. |

`render-doc` już jest podłączony i nie wymaga aktualizacji samego pinu na dzień audytu. Historyczne opisy wersji 0.1.0 i przejściowego renderera KSeF_2 w dotychczasowych dokumentach nie są aktualnym stanem integracji. Nie wykonywano tu testów uruchomieniowych ani oględzin GUI; ustalenia wynikają z kodu i dokumentacji obu aktualnych HEAD.

## 2. Referencja wyglądu i zasad KSeF

- **Referencja wizualna:** oficjalny [generator PDF faktur MF](https://github.com/CIRFMF/ksef-pdf-generator), w szczególności [generator FA(3)](https://github.com/CIRFMF/ksef-pdf-generator/blob/main/src/lib-public/FA3-generator.ts). Repozytorium generatora ma licencję MIT, ale przed przenoszeniem jakiegokolwiek kodu/nietrywialnych zasobów sprawdzić licencje zależności, warunki atrybucji i aktualne pliki. Nie zakładać, że udostępnia HTML albo że ma gotowy zgodny QR dla tego przypadku.
- **Źródło techniczne QR:** [MF / CIRF — kody QR](https://github.com/CIRFMF/ksef-api/blob/main/kody-qr.md) i [oficjalny opis kodów KSeF](https://ksef.podatki.gov.pl/informacje-ogolne-ksef-20/kody-weryfikujace-qr/).
- **Źródło treści FA(3):** [MF — struktura FA(3)](https://ksef.podatki.gov.pl/informacje-ogolne-ksef-20/struktura-logiczna-fa-3/) i [wzór FA(3) CRWDE](https://crd.gov.pl/wzor/2025/06/25/13775/).
- **Ważne rozróżnienie:** MF nie nakazuje identycznej stylistyki wizualizacji; obowiązkowa jest zgodność merytoryczna z fakturą. Celem projektu jest *zbliżenie do wzoru MF* bez deklarowania identyczności 1:1, dopóki porównanie tego nie potwierdzi. Nie korzystać w ciemno z `styl.xsl` CRWDE — jego przydatność, bezpieczeństwo i licencja nie zostały zweryfikowane.

Docelowy wydruk A4: **Faktura / numer i daty → sprzedawca i nabywca (NIP/adresy) → tabela pozycji → rozbicie VAT → kwota do zapłaty → płatność/rachunek → dodatkowe informacje → panel KSeF (QR, etykieta, czytelny link)**. Zachować wartości XML bez cichych przeliczeń, prawidłowe formatowanie PL, podział stron, czytelność wielu pozycji i długich tekstów. Układ, kolejność i odstępy należy **zmierzyć względem próbki MF**, a nie zgadywać.

## 3. Wymagania QR

### KOD I — zakres pierwszego MVP

Dla **faktury otrzymanej z KSeF z potwierdzonym numerem** wygenerować *lokalnie* link weryfikacyjny i osadzony w HTML kod QR. Zgodnie z dokumentacją MF link zawiera: bazę środowiska, `/invoice`, **NIP sprzedawcy**, **datę wystawienia P_1 w DD-MM-RRRR** i **SHA-256 oryginalnych bajtów faktury** w Base64URL. Pod kodem umieścić **numer KSeF**; sam numer nie zastępuje zawartości URL.

| Środowisko, jawnie podane przez odbiorcę API | Baza QR |
| --- | --- |
| TEST | `https://qr-test.ksef.mf.gov.pl` |
| DEMO | `https://qr-demo.ksef.mf.gov.pl` |
| PROD | `https://qr.ksef.mf.gov.pl` |

Wymogi bezpieczeństwa i poprawności:
1. QR musi kodować działający **URL weryfikacyjny MF**, nie sam numer KSeF ani adres dowolnej strony. Dołączać również jawny, klikalny `href` do tego samego URL.
2. Hash liczyć z **niezmodyfikowanych bajtów źródłowego XML**, bez ponownej serializacji, normalizacji znaków lub zmian białych znaków. Connector dziś przekazuje do adaptera `raw_xml: str` i koduje je jako UTF-8 — przed integracją ustalić, czy ten round-trip zachowuje bajty KSeF; jeśli nie, przekazać oryginalny bufor `bytes` przez uzgodnioną publiczną granicę. Jeśli dostępny jest wiarygodny hash źródłowy, porównać go.
3. Środowisko (TEST/DEMO/PROD) i **wiarygodne pochodzenie numeru KSeF** muszą być jawne; nie wnioskować z NIP, linku, nazwy firmy ani z samego XML. Brak danych → brak pozorowanego „zweryfikowanego” QR, czytelny kontrolowany status.
4. Obraz QR osadzać inline w HTML, preferencyjnie `data:image/png;base64` dla zgodności z zaobserwowanym natywnym `DKF_Html` Optimy; zbadać PNG vs SVG w docelowym podglądzie. Nie pobierać obrazu z sieci; zapis do HTML/PDF musi działać offline.
5. Domyślne HTML nie wykonuje żądań sieciowych, nie ładuje skryptów, CSS ani obrazów z obcych serwerów; **zewnętrzny URL jest tylko świadomym linkiem po kliknięciu/zeskanowaniu**. Testy braku zasobów zewnętrznych muszą uwzględnić ten wyjątek.
6. W DEMO/TEST odróżnić wydruk testowy od dokumentu produkcyjnego. Testy QR używają wyłącznie syntetycznych danych i wektorów kontrolnych.
7. QR i etykieta muszą być czytelne po wydruku; walidować odczyt skanerem z wygenerowanego obrazu/PDF, a URL w teście porównać z referencyjnym wektorem MF.

### KOD II — poza MVP odbioru faktur

Dwa kody dotyczą m.in. faktury offline **przed** przesłaniem do KSeF: KOD I z napisem `OFFLINE`, KOD II z napisem `CERTYFIKAT` i podpisem opartym na certyfikacie typu Offline. **Nie generować KODU II w pierwszym etapie** ani nie przechowywać/ładować kluczy prywatnych w `render-doc`. Po nadaniu numeru KSeF wizualizacja posiada zasadniczo jeden KOD I z numerem. Ewentualna obsługa podpisu wymaga osobnej decyzji o granicy odpowiedzialności i sekretach.

## 4. Plan realizacji — małe, niezależnie weryfikowane kroki

| Etap | Priorytet | Prace | Mierzalny odbiór |
| --- | --- | --- | --- |
| **R0 — wzorzec** | P0 | Przejrzeć istniejące API/CLI/szablony/testy. Na 3–5 syntetycznych FA(3) porównać bieżące `default` i `classic` z PDF oficjalnego generatora MF; zapisać macierz brakujących danych/elementów i 2–3 wzorcowe obrazy/podglądy bez danych klientów. | Lista różnic z priorytetami i wzorzec A4; bez zmiany produkcyjnego API. |
| **R1 — szablon KSeF** | P0 | Zaproponować osobny, opt-in `template="ksef"` oparty na istniejącym parserze i rozwiązaniach `classic`; zachować `default`/`classic`. Uporządkować layout, nagłówki, NIP, tabele, polski zapis liczb, paginację i panel QR (początkowo bez pozorowanej treści). | Wierność istotnych pól i czytelność A4/drukowania; obrazowe porównanie syntetycznych przypadków z referencją MF. |
| **R2 — QR KOD I** | P0 | Wykorzystać istniejący publiczny helper, jeżeli jest zgodny i dostępny, albo dodać minimalny niezależny komponent lokalnego tworzenia URL oraz PNG QR. Najpierw uzgodnić **jawny opcjonalny kontrakt metadanych weryfikacyjnych** (`environment`, `ksef_number`, pochodzenie/oryginalne bajty), kompatybilny wstecz; nie zmieniać domyślnego HTML. | TEST/DEMO/PROD, hash źródłowy, odczytywalny QR, link zgodny z kodem, jednoznaczne błędy przy brakach, zero połączeń sieciowych podczas renderu. |
| **R3 — connector/Optima** | P0 po R2 | **Osobne zadanie w repo connectora**: zweryfikować dostępne oryginalne bajty i metadane Receive, jawnie wybrać `ksef`, sprawdzić stabilność i wersję zależności, podgląd HTML i wydruk. Osobno kwalifikować `DKF_Html` dla Optimy, w tym charset UTF-8 deklarowany w HTML vs UTF-16LE zapisywany jako payload oraz zgodność obrazu QR/DOM. | Testy kontraktu adaptera, wizualna kontrola w docelowej wersji Optimy; **bez zmiany stanu `DKF_Html` na ready ani zapisu do bazy bez odrębnego dowodu i zgody**. |
| **R4 — rozwój po MVP** | P1/P2 | Osobno: PDF (ocena czy lepiej wykorzystać oficjalny generator czy lokalny HTML→PDF), kolejne typy FA(3), korekty/zaliczki, większa liczba podmiotów, KOD II offline. | Każdy wariant ma własne mapowanie, testy semantyczne i zgodę na rozszerzenie zakresu. |

**Najkrótsza droga:** R0 → R1 → R2, potem R3 w connectorze. Nie budować nowego GUI, usługi, silnika PDF, pełnego parsera FA(3) ani systemu certyfikatów na potrzeby tego MVP. Istniejące `classic`, przykłady i parser wykorzystywać ponownie.

## 5. Akceptacja, regresja, kontrakty

- Utrzymać `render_fa3_html(xml_bytes)` i dotychczasowe `template="default"|"classic"` **bez zmiany wyników** dla dotychczasowych testów. Nowy wygląd i QR wyłącznie przez świadomy opt-in; rozszerzenie publicznego API i wybór jego kształtu wymagają zatwierdzenia przed kodowaniem.
- Dla wspieranego profilu każda informacja merytoryczna występująca w XML ma być pokazana albo wejście jawnie odrzucone; nie zmieniać kwot, dat ani znaczenia oznaczeń.
- Testy celowane: identyczny wynik przy identycznym wejściu; źródłowy XML bez mutacji; escapowanie HTML, XML XXE/DTD, brak zasobów sieciowych, duże teksty/wiele pozycji, stawki VAT, brak/nieprawdziwe metadane QR, poprawny hash URL i etykieta.
- Kontrole wizualne: polskie znaki, dwustronicowy wydruk, długie nazwy, tabele VAT, właściwe wyrównanie liczb i zeskanowanie QR z wydruku; zrzuty tylko z syntetycznych danych.
- `DKF_Html` i specyficzne kodowanie/gzip/Optima pozostają w **connectorze**, nie w `render-doc`. Nie dopasowywać formatu zapisu SQL w samym rendererze.
- Wszelkie próbki i wyniki muszą być syntetyczne lub trwale zanonimizowane; nie commitować danych klientów, numerów rzeczywistych dokumentów, certyfikatów ani kluczy.
- Dla samej aktualizacji planu nie są wymagane testy aplikacji. Przy późniejszych zmianach R1/R2 wykonywać testy celowane, większą regresję dopiero na granicy wydania lub uzasadnionego ryzyka.

## 6. Decyzje przed implementacją

1. **Nowy `template="ksef"` (zalecane) czy przeprojektowanie istniejącego `classic`?** Zalecane nowe opt-in, bo utrzymuje kompatybilność użytkowników aktualnych szablonów.
2. **Kontrakt QR:** w jaki sposób przekazać pochodzenie numeru, środowisko i dokładne bajty; uwzględnić potwierdzony hash Receive, jeżeli istnieje. Nie przyjmować arbitralnej wartości bez weryfikacji jako dowodu faktury KSeF.
3. **Poziom podobieństwa:** „wizualnie bliski MF” (MVP) czy pixel-perfect we wszystkich wariantach (osobny koszt i szerszy projekt)? Zalecane pierwsze.
4. **PDF i użycie kodu MF:** poza MVP; oficjalny generator TypeScript/`pdfmake` może dać najwyższą zgodność PDF, ale wymaga osobnego sprawdzenia zależności, licencji i sposobu uruchamiania na Windows.

## 7. Instrukcja realizacji kolejnych zadań

Przed każdą implementacją sprawdzać bieżący `HEAD`, `AGENTS.md` (jeśli ma treść), publiczne API, istniejący CLI, `tests/test_renderer.py` i 5 przykładów `classic`. Nie tworzyć duplikatów narzędzi. CODEX wykonuje mały etap, testuje proporcjonalnie, raportuje zmienione pliki, wyniki, ograniczenia oraz lokalny commit. Push, tag i Release wymagają osobnej zgody; nie zmieniać zależności w connectorze w zadaniu `render-doc`. Każde rozszerzenie publicznego API, integracji i obsługi sekretów uzgodnić wcześniej.

**Kolejna kontrola:** pełne testy integracyjne R1 oraz wizualne porównanie MF ↔ HTML na identycznych syntetycznych XML. **Kolejny etap funkcjonalny:** R2 — prawidłowy QR KOD I, po domknięciu QA R1; bez zmiany Optimy i zależności connectora w tej publikacji.
