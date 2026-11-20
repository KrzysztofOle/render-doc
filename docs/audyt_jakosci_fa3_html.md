# Audyt jakości renderowania FA(3) XML → HTML

- **Data:** 2026-10-14
- **Wersja:** render-doc 0.1.0
- **Wynik:** **PARTIAL**
- **Zakres:** ograniczony profil podstawowej faktury VAT w PLN, stawka 23%; bez pełnej walidacji XSD.

Audyt porównał mapowanie w `src/render_doc/renderer.py` z broszurą informacyjną FA(3) Ministerstwa Finansów ([oficjalna broszura](https://ksef.podatki.gov.pl/media/jknpcymf/broszura-informacyjna-dotyczaca-struktury-logicznej-fa-3-04032026.pdf)) i zsyntetyzowanym XML-em używanym przez testy. Nie użyto danych klientów. Sam wynik HTML nie został uznany za dowód poprawności wizualnej.

## Mapowanie pól

| Pole FA(3) | Znaczenie według FA(3) | Prezentacja w HTML | Wynik kontroli |
|---|---|---|---|
| `Fa/P_2` | Numer faktury nadany przez podatnika | Nagłówek „Numer” i tytuł dokumentu | PASS; wartość zgodna z wejściem |
| `Fa/P_1` | Data wystawienia | Nagłówek „Data wystawienia” | PASS; data walidowana i zgodna z wejściem |
| `Podmiot1/DaneIdentyfikacyjne/Nazwa`, `NIP` | Dane sprzedawcy | Sekcja „Sprzedawca”, nazwa i NIP | PASS dla obsługiwanego wariantu; nazwa i NIP są wymagane |
| `Podmiot2/DaneIdentyfikacyjne/Nazwa`, `NIP` | Dane nabywcy | Sekcja „Nabywca”, nazwa i NIP | PASS dla obsługiwanego wariantu; nazwa i NIP są wymagane |
| `Podmiot1/Podmiot2/Adres/{KodKraju,AdresL1,AdresL2}` | Kraj i linie adresu podmiotu | Właściwa sekcja kontrahenta | PASS dla tych pól; brak całego adresu i brak `AdresL2` są akceptowane |
| `Fa/FaWiersz/P_7` | Nazwa/opis pozycji | Kolumna „Opis” | PASS; tekst zgodny, znaki HTML są escapowane |
| `FaWiersz/NrWierszaFa` | Numer kolejny pozycji | Nie jest wyświetlany | **PARTIAL:** element jest akceptowany, ale cicho pomijany |
| `FaWiersz/P_8A`, `P_8B` | Jednostka miary i ilość | Kolumna „Ilość i jednostka” | **PARTIAL:** ilość jest wyświetlana; opcjonalny brak `P_8A` daje widoczną pustą jednostkę (`1 `) |
| `FaWiersz/P_9A` | Cena jednostkowa netto | Kolumna „Cena netto” | PASS dla obsługiwanego wariantu; wartość bez przeliczania |
| `FaWiersz/P_11` | Wartość netto pozycji | Kolumna „Wartość netto” | PASS dla obsługiwanego wariantu; zgodna z wejściem |
| `FaWiersz/P_12` | Stawka podatku dla pozycji | Kolumna „VAT” | PASS dla wartości `23`; pozostałe stawki są odrzucane |
| `Fa/P_13_1`, `P_14_1`, `P_15` | Zbiorcza podstawa netto, podatek i należność ogółem | Podsumowanie netto, VAT i „Należność ogółem (brutto)” | PASS dla prostego profilu 23%: wejściowe `100.00`, `23.00`, `123.00` są zachowane; etykietę „brutto” warto uprościć do „Należność ogółem” |

Mapowanie nie wylicza ani nie uzgadnia kwot między pozycjami a sumami. Dla kontrolowanego syntetycznego przykładu render zachował numer, datę, NIP-y, adresy, opis, ilość, cenę, netto, stawkę i sumy. Ograniczony allowlist odrzuca nieznane elementy, w tym dodatkowe pola faktury i pozycje, zamiast renderować niepełny wariant. Nie jest to walidacja całej struktury ani wszystkich warunków XSD FA(3).

## Bezpieczeństwo i odporność

- **XML/XXE/DTD:** PASS w zakresie sprawdzonym. Parser ma `resolve_entities=False`, `load_dtd=False`, `no_network=True`; dokument z deklaracją DTD jest odrzucany. Istniejący test lokalnej zewnętrznej encji przechodzi; niezależna próba DTD także została odrzucona.
- **Niepoprawny XML i obca struktura:** PASS; błędny XML daje `InvalidXmlError`, struktura spoza FA(3) `UnsupportedDocumentError`.
- **Wstrzyknięcie HTML/JS:** PASS dla sprawdzonych pól tekstowych. Wartości `<script>` i `<img ... onerror=...>` pojawiły się jako tekst escapowany, bez elementów aktywnych.
- **Zasoby zewnętrzne:** PASS dla wygenerowanego dokumentu: CSS jest osadzony, brak JavaScriptu, odnośników, obrazów, fontów zewnętrznych i odwołań `url(...)`.
- **Sieć:** PASS w zakresie testu. Istniejący test blokuje `socket.connect` i `socket.create_connection` podczas renderowania; parser jest skonfigurowany bez sieci. Nie prowadzono przechwytywania ruchu systemowego.
- **Niepełne pola i warianty:** nieobsługiwane elementy i stawki są odrzucane. Opcjonalny adres jest pomijany poprawnie, ale opcjonalna jednostka pozostawia pusty fragment w komórce ilości.

## Kontrola wizualna

**NOT VERIFIED.** CLI wygenerowało HTML z syntetycznego fixture, ale rzeczywiste otwarcie i oględziny w Safari nie powiodły się: narzędzie kontroli komputera zgłosiło oczekujące uprawnienia Accessibility i Screen Recording. Nie oceniam więc jako PASS układu kontrahentów, szerokiej tabeli, wyrównania kwot, druku ani polskich znaków w renderowanej przeglądarce. Długie nazwy i opisy również nie zostały wizualnie sprawdzone. Kod zawiera responsywną regułę dla wąskiego ekranu i prostą regułę `@media print`, lecz sam odczyt CSS nie potwierdza wyglądu.

## Problemy, waga i zalecenia

1. **Niska:** `NrWierszaFa` jest dopuszczony przez parser, lecz nie trafia do tabeli. Zalecenie: wyświetlić numer albo odrzucać ten element/profil, aby nie sugerować pełnego odwzorowania. Reprodukcja: użyć syntetycznego wiersza z `NrWierszaFa=1`; wygenerowany HTML nie pokazuje numeru.
2. **Niska:** brak opcjonalnego `P_8A` pozostawia ilość ze spacją i pustą jednostką. Reprodukcja: usunąć `<P_8A>szt.</P_8A>` z syntetycznego fixture; HTML zawiera `1 </td>`. Zalecenie: warunkowo nie renderować separatora, gdy jednostki brak.
3. **Niska:** etykieta sumy mówi „Należność ogółem (brutto)”, podczas gdy `P_15` jest polem należności ogółem. Dla obsługiwanego prostego przykładu wyniki się pokrywają; zalecenie: etykieta „Należność ogółem”.
4. **Ograniczenie weryfikacji:** brak wizualnych oględzin Safari i podglądu wydruku. Zalecenie: po udostępnieniu wymaganych uprawnień wykonać kontrolę na krótkim i długim syntetycznym dokumencie oraz w podglądzie wydruku.

Nie wykryto w tym audycie cichego pomijania całych pozycji ani nieobsługiwanych pól faktury: nieznane pola są odrzucane. Ustalenie o `NrWierszaFa` dotyczy pola wewnątrz zaakceptowanego wiersza.

## Wykonane kontrole

- `python3 -m pytest -q` — **PASS**, 11 testów.
- Niezależne wywołanie publicznego API na fixture — wartości źródłowe obecne i zgodne.
- Próby DTD oraz tekstów przypominających `<script>`/`<img>` — DTD odrzucone, markup escapowany.
- Brak adresu i `P_8A` — wariant akceptowany; wykryto pusty separator jednostki.
- CLI `render-doc input.xml --output output.html` na pliku tymczasowym — kod 0; wynik identyczny z API.
- Otworzenie HTML i sprawdzenie wyglądu w Safari — **NOT VERIFIED** z powodu oczekujących uprawnień narzędzia.
- Zgodnie z zakresem nie zmieniano kodu ani testów; fixture i wygenerowane pliki pozostawały tymczasowe.

## Automatyczne porównanie źródła z HTML (2026-11-20)

Dodano wewnętrzną kontrolę pytest `tests/test_source_html_consistency.py` dla
szablonu `ksef`. Oczekiwane dane są niezależnie odczytywane z oryginalnych
fixture XML przez `xml.etree.ElementTree`, a HTML parsowany do prostego drzewa
testowego. Porównanie jest strukturalne: kontroluje właściwą kartę sprzedawcy
i nabywcy, tabelę wszystkich pozycji, tabelę sum stawek VAT, sekcję płatności
i rachunku oraz tabelę dodatkowych opisów. Entitie HTML są dekodowane przez
parser; format dat i dziesiętnych porównywany jest dokładnie, bez zmiany
wartości źródłowych i bez przeliczania kwot.

Automatycznie porównywane są: numer faktury; daty wystawienia i dostawy;
waluta; nazwy, NIP-y i adresy sprzedawcy/nabywcy we właściwych kartach; dla
każdej pozycji numer wiersza, opis, ilość, jednostka, cena jednostkowa netto,
stawka VAT i wartość netto; źródłowe podstawy i kwoty VAT per stawka; `P_15`
jako należność ogółem; termin, forma i rachunek płatności; wszystkie ogólne
`DodatkowyOpis`. Wartości są porównywane w sekcjach/tabelach właściwych dla
danych, nie jako swobodny tekst całego dokumentu. Daty i formatowanie
dziesiętne są sprawdzane dokładnie, z zachowaniem polskich znaków i dekodowaniem
encji HTML.

Pięć wersjonowanych syntetycznych fixture'ów obejmuje jedną pozycję 23%,
stawki mieszane 23%/8%, wiele pozycji z długimi nazwami, przelew z
terminem/formą/rachunkiem oraz warianty 0% krajowe/WDT/eksport. Testy
niezależnej macierzy dodatkowo adaptują w pamięci fixture jednopozycyjny do
5% (`P_12`, `P_13_3`, `P_14_3`) oraz `zw` (`P_12`, `P_13_7`), bez tworzenia
nowych fixture'ów. Dla sum sprawdzane są źródłowe podstawy i kwoty VAT per
stawka, sprzedaż zwolniona oraz `P_15`; dla kategorii bez sumarycznego VAT
sprawdzane jest oznaczenie „—”, bez fikcyjnej kwoty 0,00. Informacyjna kolumna
brutto per stawkę nie jest rekonstruowana jako wartość źródłowa.

Fixture'y zawierają tylko jawnie nieaktywne oznaczenia `Adnotacje`, które
istniejący renderer waliduje i celowo nie prezentuje. Aktywne oznaczenia,
rabaty i nieobsługiwane dane dodatkowe nie należą do tej macierzy; renderer ma
je odrzucić zamiast częściowo wyrenderować.

Testy negatywne modyfikują wynik HTML i potwierdzają wykrycie zmienionego NIP-u,
rzeczywistej zamiany kompletnej zawartości kart sprzedawcy i nabywcy przy
zachowaniu etykiet i wszystkich wartości dokumentu, błędnych sum VAT 23% i 5%,
zmienionej wartości sprzedaży zwolnionej, brakującej pozycji, podmienionej
wartości pozycji i usuniętego rachunku. Osobny przypadek potwierdza odrzucenie
rodzaju faktury KOR zamiast częściowego renderu. Istniejące testy
`test_renderer.py` i `test_ksef_template.py` nadal pokrywają punktowe mapowania,
escaping, bezpieczeństwo zasobów, deterministyczność oraz inne odmowy; nowy QA
uzupełnia je o porównanie end-to-end XML → sekcja HTML.

Weryfikacja rozszerzenia (2026-11-20): `tests/test_source_html_consistency.py`
— `16 passed`; pełny lokalny zestaw render-doc — `141 passed, 1 skipped`.
Pominięty test wizualny wymaga opcjonalnych `cv2`/`numpy`. `ruff check` z
pominięciem zastanych naruszeń `I001` i `RUF012` przechodzi. Pełny lint nadal
zgłasza te dwa naruszenia w niezmienionych wcześniejszych liniach pliku;
`ruff format --check` również wskazuje zastane formatowanie poza dodanym
fragmentem. `pip check` nie wykrył problemów zależności, a import pakietu i
zależności runtime zakończył się powodzeniem. Repozytorium connectora i jego
walidator `DKF_Html` nie były zmieniane.

Uruchomienie:

```sh
py -3.12 -m pytest -q tests/test_source_html_consistency.py
```

Zakres jest ograniczony do pięciu fixture'ów, dwóch wariantów syntetycznie
adaptowanych w pamięci oraz danych i pól objętych asercjami. To nie waliduje
XSD ani wszystkich możliwych FA(3), nie
jest oceną wizualną i nie dowodzi zgodności bajtowej/semantycznej z Comarch lub
MF. Korekty, zaliczki i inne nieobsługiwane struktury nadal muszą być odrzucone.
Wynik nie kwalifikuje `DKF_Html` do zapisu ani nie zmienia `ContractValidator`.

Wcześniejsze uwagi audytu o pomijaniu `NrWierszaFa` i pustym separatorze
opcjonalnej jednostki są nieaktualne względem bieżącego kodu: obecny szablon
pokazuje numer źródłowego wiersza i zastępuje brak jednostki kreską; pokrywa to
istniejący `test_ksef_template.py`. Pozostałe zastrzeżenia wizualne z audytu
pozostają bez zmian.
