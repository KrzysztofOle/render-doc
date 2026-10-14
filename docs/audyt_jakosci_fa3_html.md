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
