# Kwalifikacja kandydata render-doc 0.3.0

2026-11-22. **RELEASE_CANDIDATE_READY** w zakresie technicznym.
Proponowany tag to `v0.3.0`. Finalna rewizja i sumy obu artefaktów są
w pakiecie decyzji `P0-RELEASE-FINALIZATION-01` w repozytorium Connectora.

- Publiczne `render_fa3_html` działa z dotychczasowymi parametrami i
  wyjątkami. Kandydat prezentuje jedną aktywną podstawę zwolnienia A, B
  albo C. Brutto grup 0% i `zw` pochodzi z netto źródła.
  [Profil i API](../README.md#obsługiwany-zakres).
- Pełna regresja na Pythonie 3.10.21 w Linuksie dała 179 PASS
  i 90,10% pokrycia gałęzi i instrukcji. Obejmuje niezależne dekodowanie
  QR, porównanie XML z widocznym HTML, polskie znaki, białe znaki, długie
  opisy, escapowanie, brak DTD i zewnętrznych zasobów. Końcowa regresja
  Windows na Pythonie 3.12.10 z OpenCV 4.13.0 dała 179 PASS i 90,10%.
- Wheel i sdist sprawdzono pod kątem metadanych, wymaganych plików i
  sekretów. Obie formy przechodzą instalację i import spoza checkoutu.
  Metadane i dołączony plik wskazują Apache-2.0. [Licencja](../LICENSE).

Końcowa poprawka zachowuje bezpośrednie uruchamianie narzędzia QA i
import kodu z checkoutu. Dotyczy kolejności importu w teście. Runtime,
szablony, podpis funkcji i typy wyjątków mają ten sam kontrakt.
Pełny Ruff przechodzi.

## Zmiany od 0.2.0

- Szablony prezentują jedną aktywną podstawę zwolnienia `P_19A/B/C`.
  Brutto grup 0% i `zw` korzysta z kwoty netto ze źródła. Profil obejmuje
  udokumentowane kombinacje 23%, 8%, 5%, 0% i `zw`.
- Porównanie lokalnej pary XML i HTML sprawdza wartości księgowe w
  odpowiadających sekcjach. Subprocess zwraca bezpieczny status i kod
  przyczyny.
- Metadane dystrybucji wskazują 0.3.0 i dołączoną licencję Apache-2.0.

## Pakiet decyzji

Do publikacji zatwierdzić osobno dokładny commit, tag `v0.3.0`, Release,
`render_doc-0.3.0-py3-none-any.whl` i `render_doc-0.3.0.tar.gz`.
Sumy porównać z końcowym raportem. Zbudowanie z eksportu Git można
odtworzyć przez `git archive` i `uv build --offline`; czasy kontenerów
mogą się różnić.

Po publikacji sprawdzić peeled SHA tagu i pochodzenie PEP 610.
Zaktualizować pin w izolowanym środowisku, uruchomić `pip check`,
macierz VAT i admission, następnie podjąć decyzję o promocji pinu.
Jeśli walidacja zawiedzie, przywrócić poprzedni TOML i zainstalować
render-doc 0.2.0 z commita `6596bfc7efcb98c45253b00be403a9e2eac26d0c`.
Powtórzyć kontrolę instalacji i źródła Git.

Kwalifikacja obejmuje HTML i QR. Zgodność z polem `DKF_Html` Optimy
wymaga własnego dowodu.
