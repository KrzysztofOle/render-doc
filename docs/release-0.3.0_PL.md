# Kwalifikacja kandydata render-doc 0.3.0

2026-11-22. **RELEASE_CANDIDATE_READY** w zakresie technicznym.
Artefakty pochodzą z rewizji `69d4ad6b41bba99fd285f3e65178bfaefb31d09f`.

- Publiczne `render_fa3_html` działa z dotychczasowymi parametrami i
  wyjątkami. Kandydat prezentuje jedną aktywną podstawę zwolnienia A, B
  albo C. Brutto grup 0% i `zw` pochodzi z netto źródła.
  [Profil i API](../README.md#obsługiwany-zakres).
- Pełna regresja na Pythonie 3.10.21 w Linuksie dała 179 PASS
  i 90,10% pokrycia gałęzi i instrukcji. Obejmuje niezależne dekodowanie
  QR, porównanie XML z widocznym HTML, polskie znaki, białe znaki, długie
  opisy, escapowanie, brak DTD i zewnętrznych zasobów. Na Windows Python
  3.12.10 było 178 PASS i 1 SKIP opcjonalnego dekodera OpenCV.
- Wheel i sdist sprawdzono pod kątem metadanych, wymaganych plików i
  sekretów. Obie formy przechodzą instalację i import spoza checkoutu.
  Metadane i dołączony plik wskazują Apache-2.0. [Licencja](../LICENSE).

| Artefakt | SHA-256 |
| --- | --- |
| `render_doc-0.3.0-py3-none-any.whl` | `1aa79f57bde11cd1d8dbbd8aff17b080ac4a4fe238beac5d7cecd6d494f941d6` |
| `render_doc-0.3.0.tar.gz` | `50a75c91bf631d7280c289b21164dcb8086a4a2afb5b3c0f3f26d953a05bfe35` |

Brak dowodu zgodności z polem `DKF_Html` Optimy. Tag, push i Release
pozostają przedmiotem osobnej decyzji właściciela.
