# Audyt pokrycia FA(3) na trzech dokumentach Receive

## Cel i wynik

Audyt określa najmniejszy zakres obsługi potrzebny do wyrenderowania trzech
lokalnych dokumentów FA(3) odebranych wcześniej z KSeF DEMO. Nie zmieniono
renderera, API, CLI ani klienta KSeF. Nie kopiowano XML/HTML ani danych stron do
repozytorium.

Wynik: trzy dokumenty mają zgodne zapisane SHA-256 i identyczny istotny kształt
struktury. Wszystkie trzy są podstawowymi fakturami `VAT` w PLN, z `JST=2`,
`GV=2`, bez `Podmiot3`, z jedną pozycją, jedną datą `P_6`, adnotacjami
oznaczającymi brak szczególnych procedur oraz jednym niepowiązanym z pozycją
wpisem `DodatkowyOpis`. Po ostatniej zmianie renderer nadal odrzuca je na
`P_6`, `Adnotacje` i `DodatkowyOpis`. Po ich ścisłej obsłudze nie stwierdzono
drugiej nieobsługiwanej struktury w tych XML.

Ten wynik dotyczy wyłącznie trzech przeanalizowanych dokumentów. Nie jest
walidacją XSD ani dowodem obsługi wszystkich poprawnych faktur FA(3).

## Metoda i ochrona danych

- Sprawdzono `main`, HEAD, upstream i status przed audytem.
- Trzy rekordy `received_documents` odczytano z dwóch lokalnych baz
  `ksef2-test-client` przez URI SQLite `mode=ro`; bazy nie były modyfikowane.
- Każdy zapisany hash SHA-256 porównano z bajtami XML. Wszystkie trzy
  porównania były zgodne.
- XML parsowano in-memory przez `lxml` z `resolve_entities=False`,
  `load_dtd=False`, `no_network=True`, `recover=False` i `huge_tree=False`.
- Do analizy zapisano jedynie nazwy elementów, liczniki, wartości kontrolne
  wyliczeniowe i wyniki porównań. Nie zapisano identyfikatorów, wartości
  biznesowych, hashy, XML ani HTML.
- `AGENTS.md` w checkoutcie jest pusty. Istniejącym zestawem testów jest
  `tests/test_renderer.py`; audyt wykorzystał go bez dodawania narzędzi.

## Struktura trzech dokumentów

We wszystkich trzech dokumentach potwierdzono:

- właściwy namespace i nagłówek FA(3) `1-0E`, wariant formularza `3`;
- `Podmiot1`, `Podmiot2`, ich dane identyfikacyjne i adres sprzedawcy;
- `Podmiot2/JST=2` oraz `Podmiot2/GV=2`; brak `Podmiot3`;
- `Fa/RodzajFaktury=VAT`, `KodWaluty=PLN`, pola numeru i daty wystawienia;
- obecne `P_6`, o prawidłowym formacie daty i wartości równej `P_1`;
- po jednej pozycji z polami `NrWierszaFa`, `P_7`, `P_8A`, `P_8B`, `P_9A`,
  `P_11`, `P_12`; wykryta stawka ma odpowiadające podsumowanie netto i VAT;
- `P_15` oraz następujące grupy spoza obecnego allowlistu: `Adnotacje` i
  `DodatkowyOpis`.

W `Adnotacje` każde wejście ma wartości `2` dla `P_16`, `P_17`, `P_18`,
`P_18A` i `P_23`, oraz ujemne znaczniki `P_19N`, `P_22N` i `P_PMarzyN`.
Występują odpowiednio węzły `Zwolnienie/P_19N`,
`NoweSrodkiTransportu/P_22N` i `PMarzy/P_PMarzyN`. Żaden z trzech
dokumentów nie zawiera dodatniego wariantu tych procedur ani danych
uzupełniających dla nich.

Każdy `DodatkowyOpis` zawiera `Klucz` i `Wartosc`; nie zawiera `NrWiersza`.
Treść tych pól pozostaje w samych dokumentach i nie jest częścią raportu.

## Znaczenie pól wymagających szczególnego traktowania

### `P_6`

MF opisuje `P_6` jako datę dokonania/zakończenia dostawy, wykonania usługi albo
otrzymania określonej zapłaty, jeśli ta data jest ustalona i różni się od daty
wystawienia. Używa się go, gdy data jest wspólna dla wszystkich pozycji. Gdy
daty różnią się pomiędzy pozycjami, właściwe jest `P_6A` w wierszach; dla
okresu rozliczeniowego występują osobne pola `OkresFa/P_6_Od` i `P_6_Do`.
Format daty to `RRRR-MM-DD`. Zob. broszurę MF, opis `P_6` i `P_6A`, s. 44 oraz
86–87 ([oficjalny PDF](https://ksef.podatki.gov.pl/media/jknpcymf/broszura-informacyjna-dotyczaca-struktury-logicznej-fa-3-04032026.pdf)).

W trzech dokumentach `P_6` jest syntaktycznie prawidłowy i równy `P_1`. Broszura
MF opisuje `P_6` jako pole stosowane, gdy data różni się od daty wystawienia;
audyt odnotowuje więc tę rozbieżność między warunkiem opisowym a rzeczywistymi
dokumentami przyjętymi przez KSeF. Wartość trzeba odczytać i zweryfikować, a w
HTML zachować ją pod osobną etykietą daty dostawy/wykonania usługi, nawet jeśli
data kalendarzowa pokrywa się z datą wystawienia. Nie przyjmować `P_6A` ani
`OkresFa` w tym etapie.

### `Adnotacje`

MF definiuje tu oznaczenia związane ze szczególną interpretacją faktury:

- `P_16`: metoda kasowa; `1` oznacza zastosowanie, `2` jej brak.
- `P_17`: samofakturowanie; `1` oznacza zastosowanie, `2` jego brak.
- `P_18`: odwrotne obciążenie; `1` oznacza zastosowanie, `2` jego brak.
- `P_18A`: mechanizm podzielonej płatności; `1` oznacza zastosowanie, `2`
  jego brak.
- `Zwolnienie`: pola `P_19` i podstawa prawna opisują zwolnienie; alternatywne
  `P_19N=1` oznacza brak sprzedaży zwolnionej.
- `NoweSrodkiTransportu`: dotyczy dostawy nowych środków transportu; alternatywne
  `P_22N=1` oznacza brak takiej dostawy.
- `P_23`: oznaczenie uproszczonej transakcji trójstronnej w UE; `1` ją oznacza,
  `2` jej brak.
- `PMarzy`: oznacza procedurę VAT marża; alternatywne `P_PMarzyN=1` oznacza
  brak tej procedury.

Źródło: broszura MF, tabele 29–33, s. 53–63 ([oficjalny PDF](https://ksef.podatki.gov.pl/media/jknpcymf/broszura-informacyjna-dotyczaca-struktury-logicznej-fa-3-04032026.pdf)).

W badanych dokumentach wszystkie te znaczniki wskazują, że szczególne tryby nie
mają zastosowania. Można pominąć je w widoku dopiero po walidacji dokładnie
obsługiwanego zestawu wartości oraz relacji wyboru (np. `P_19N` zamiast `P_19`
z podstawą zwolnienia). Nie wolno pomijać dowolnych dzieci `Adnotacje` ani
akceptować wartości dodatnich, bo mogłoby to zmienić informację o rozliczeniu
VAT, stronach procesu lub wymaganym oznaczeniu faktury. Dodatni wariant powinien
pozostać odrzucony do osobnego etapu obsługi i prezentacji.

### `DodatkowyOpis`

To pole powtarzalne (do 10 000 wystąpień) typu klucz-wartość do dodatkowych
informacji na fakturze. Opcjonalne `NrWiersza` wiąże opis z wierszem faktury
(`NrWierszaFa`) albo zamówienia (`NrWierszaZam`); bez niego wpis jest
informacją ogólną. Broszura MF pokazuje zarówno dane
ogólne, jak i wiele wpisów przypisanych do wielu wierszy (przykład 20, s. 81–84;
[oficjalny PDF](https://ksef.podatki.gov.pl/media/jknpcymf/broszura-informacyjna-dotyczaca-struktury-logicznej-fa-3-04032026.pdf)).

W każdym badanym dokumencie jest jeden wpis ogólny. Jest to treść faktury,
więc pominięcie powoduje utratę informacji, nawet jeśli nie zmienia obliczeń
VAT. Minimalna bezpieczna prezentacja to sekcja „Dodatkowe informacje” z
widoczną parą klucz-wartość, z escapowaniem HTML. Dla wpisów z `NrWiersza`
trzeba zachować powiązanie z właściwą pozycją; gdy powiązania nie da się
zweryfikować, renderer powinien odmówić renderowania zamiast zamieniać opis w
informację ogólną.

## Pokrycie elementów istotnych dla profilu

Legenda: **A** — obsługiwane i prezentowane; **B** — sprawdzane lub
bezpiecznie pomijane jako metadane/znacznik braku wariantu; **C** — nieobsługiwane,
ale potrzebne do tych trzech dokumentów; **D** — celowo poza zakresem obecnego
etapu; **E** — niebezpieczne do bezwarunkowego pomijania.

| Pole/struktura | Występuje w DEMO | Obsługiwane | Wymaga prezentacji | Wpływ na interpretację | Priorytet | Rekomendowane działanie |
|---|---:|---|---|---|---|---|
| `Naglowek/KodFormularza`, `WariantFormularza` | Tak | A/B: ścisła kontrola identyfikatora, wersji i wariantu | Nie | Identyfikuje schemat | P0 | Zachować obecną walidację `FA (3)`, `1-0E`, wariant `3` |
| `DataWytworzeniaFa`, `SystemInfo` | Tak | B: wymagany czas tylko sprawdzany jako niepusty; `SystemInfo` ignorowane | Zwykle nie | Czas utworzenia XML i nazwa systemu, nie data sprzedaży | P2 | Nie dodawać do podglądu podstawowej faktury; format czasu pozostaje ograniczeniem walidacji |
| `Podmiot1`, `Podmiot2`: identyfikacja i adres | Tak | A | Tak | Tożsamość sprzedawcy i nabywcy | P0 | Zachować nazwę, NIP i obsługiwane linie adresu; nie poszerzać allowlistu stron bez potrzeby |
| `Podmiot2/JST`, `GV` | Tak | B: `2` walidowane po ostatnim commicie | Nie | `1` wymaga dodatkowego odbiorcy w `Podmiot3` | P0 | Zachować ścisłe `2`; odrzucać `1`, brak i wartości spoza słownika |
| `Podmiot3` | Nie | D: odrzucany na korzeniu | Zależnie od roli | Może wskazywać odbiorcę, płatnika, JST/GV lub inny podmiot | P0 | Pozostawić poza zakresem; nigdy nie ignorować |
| `Fa/RodzajFaktury` | Tak: `VAT` | A: akceptuje tylko `VAT` | Typ jest odzwierciedlony przez dokument | Korekta, zaliczka, rozliczenie i uproszczenie mają odrębną semantykę | P0 | Utrzymać odrzucanie innych rodzajów |
| `KodWaluty`, `P_1`, `P_2` | Tak | A; `P_1` jest sprawdzane jako data | Tak | Waluta i identyfikacja/data wystawienia | P0 | Zachować mapowanie; inne waluty wymagają osobnej obsługi kwot i kursów |
| `P_6` | Tak; równe `P_1` we wszystkich trzech | C | Tak jako osobno opisana data dostawy/usługi, jeśli obecna | Może różnić się od daty wystawienia; znaczenie podatkowe czasowe | P0 | Walidować ISO date i pokazać osobno; odrzucać na tym etapie `P_6A` i `OkresFa` |
| `FaWiersz`: `NrWierszaFa`, `P_7`, `P_8A/B`, `P_9A`, `P_11`, `P_12` | Tak; jeden wiersz w każdym | A dla zaobserwanych pól | Tak | Opis, ilość, cena, podstawa i stawka | P0 | Zachować obecne mapowanie i escapowanie; bez poszerzania o pola pozycji nieobecne w próbie |
| Podsumowanie `P_13_1`, `P_14_1`, `P_15` | Tak; 23% i suma ogółem | A | Tak | Podstawa opodatkowania, VAT i kwota należności | P0 | Zachować źródłowe wartości; nie wyliczać ani nie uzgadniać ich po cichu |
| Inne pola sumaryczne VAT (`P_13_*`, `P_14_*`) | Nie w próbie poza 23% | C/D zależnie od kategorii | Tak, gdy użyte | Inne stawki, zwolnienie, odwrotne obciążenie, marża i inne tryby | P1 | Osobne mapowanie i walidacja warunków; obecne stawki 8%, 5%, 0% są ograniczonym istniejącym profilem, resztę odrzucać |
| `Fa/Adnotacje` i znaczniki procedur | Tak; wyłącznie wartości „brak” | C: całe poddrzewo odrzucane przez allowlistę `Fa` | Nie dla zwalidowanego zestawu braków | Wartości dodatnie wpływają na oznaczenie i sposób rozliczenia | P0 | Akceptować wyłącznie enumeracje i relacje potwierdzone w trzech plikach; dodatnie/nieznane warianty nadal odrzucać |
| `Fa/DodatkowyOpis/Klucz`, `Wartosc` | Tak; po jednym wpisie bez odwołania do pozycji | C | Tak | Informacja dodatkowa; bez własnej matematyki VAT, ale jest częścią treści faktury | P0 | Wyświetlić wszystkie wpisy jako escapowane pary klucz-wartość |
| `DodatkowyOpis/NrWiersza` | Nie | D/E: brak obsługi | Tak przy wystąpieniu, w kontekście pozycji | Wskazuje pozycję, której dotyczy opis | P1 | W minimalnym etapie odrzucać; osobno obsłużyć walidację referencji i prezentację przy wierszu |
| `Platnosc`, `Rozliczenie`, `WarunkiTransakcji`, `Zamowienie` | Nie | D/E: odrzucane | Zależnie od pól | Mogą opisywać zapłatę, pozostałe saldo, potrącenia, warunki lub zamówienie | P1 | Pozostawić odrzucanie; nie usuwać z allowlisty bez mapowania i reguł zależności |
| `PodmiotUpowazniony`, `Stopka`, `Zalacznik` | Nie | D/E: odrzucane | Występowanie może wymagać prezentacji | Upoważnienie, dodatkowe informacje i załączona treść | P1 | Pozostawić odrzucanie; osobne etapy, w szczególności załącznik wymaga własnych ograniczeń |
| Korekty, zaliczki, faktury rozliczeniowe/uproszczone, VAT marża | Nie jako typ faktury; jedynie jawne znaczniki braku procedur | D: odrzucane/nieobsługiwane | Tak, po osobnej implementacji | Zmieniają strukturę kwot, stronę korekty lub podstawę/kwotę należności | P0 | Nie akceptować przez ogólny `VAT` path ani przez ignorowanie pól sterujących |

## Minimalny etap dla wyniku 3/3

Proponowany jest jeden wąski etap, bez zmiany publicznego API i bez nowych
zależności:

1. Rozszerzyć walidację dozwolonych bezpośrednich elementów `Fa` dokładnie o
   `P_6`, `Adnotacje` i `DodatkowyOpis`; reszta allowlistów pozostaje ścisła.
2. Dla `P_6` zaakceptować wyłącznie pojedynczą poprawną datę ISO i pokazać ją
   z etykietą daty dostawy/wykonania usługi. Odrzucić `P_6A`, `OkresFa` oraz
   inne źródła dat sprzedaży.
3. Dla `Adnotacje` walidować dokładne obecne znaczniki nieaktywności i
   wzajemne wykluczenia (`P_19N`, `P_22N`, `P_PMarzyN` zamiast aktywnych
   wariantów; wartości „brak” dla pozostałych flag). Po walidacji można nie
   drukować samych znaczników. Każda wartość aktywna, nieznana lub sprzeczna
   ma nadal kończyć się `UnsupportedDocumentError`.
4. Dla `DodatkowyOpis` walidować obecny wariant bez `NrWiersza`, wymagający
   niepustych `Klucz` i `Wartosc`, i prezentować wpisy (także powtarzane)
   w sekcji dodatkowych informacji. Wszystkie wartości tekstowe escapować.
   Na tym etapie odrzucać powiązania `NrWiersza`, bo badane dokumenty ich nie
   używają.
5. Dodać syntetyczne regresje dla każdej ścieżki pozytywnej, braków/duplikatów,
   błędnych dat, aktywnych i sprzecznych adnotacji, wielokrotnych opisów,
   escapowania, deterministyczności oraz odrzucania `P_6A`, okresów, `Podmiot3`
   i innych nieobsługiwanych elementów. Na końcu powtórzyć offline render trzech
   lokalnych rekordów w trybie SQLite read-only.

### Zmiany opcjonalne, niewymagane dla tych dokumentów

- Obsługa `DodatkowyOpis/NrWiersza` z walidacją referencji zarówno do wierszy
  faktury, jak i zamówienia oraz prezentacją przy właściwym wierszu.
- Prezentacja dodatnich wariantów `Adnotacje`, `P_6A` i `OkresFa`; wymagają
  osobnych testów semantycznych i nie powinny być domyślnie akceptowane.
- Silniejsza walidacja `DataWytworzeniaFa`; obecny parser sprawdza tylko, czy
  pole nie jest puste.

Element opcjonalny nie staje się bezpieczny do ignorowania tylko dlatego, że
może go nie być. W tym etapie akceptacja jest ograniczona do zweryfikowanego
profilu; wszystkie warianty nieprzedstawione w tabeli pozostają odrzucane.

## Ryzyko

| Ryzyko | Ocena | Ograniczenie w rekomendowanym etapie |
|---|---|---|
| Błędna prezentacja znaczenia podatkowego | Wysokie przy ogólnym ignorowaniu `Adnotacje`; niskie–średnie przy ścisłym profilu | Walidować zamknięte wartości i relacje; wszystkie aktywne tryby nadal odrzucać |
| Utrata treści faktury | Wysokie przy pominięciu `DodatkowyOpis`; niskie po jego prezentacji | Renderować każde `Klucz`/`Wartosc`, escapować HTML; nie pomijać kolejnych wpisów |
| Pomylenie daty sprzedaży z wystawieniem | Średnie | Osobna etykieta dla `P_6`; osobne warianty `P_6A` i okresu pozostają zablokowane |
| Regresja istniejących faktur | Niskie–średnie | Zachować obecną ścieżkę i allowlisty poza trzema nazwanymi grupami; testy obecne i nowe |
| Osłabienie walidacji XML / akceptacja obcych wariantów | Wysokie przy ignorowaniu nieznanych dzieci; niskie przy ograniczonym allowliście | Nie zastępować `_children` ignorowaniem; sprawdzić krotności, wymagane pola, enumeracje i zależności |

## Narzędzia, testy i ograniczenia audytu

- Użyto istniejącego parsera `lxml`, testów pytest i dokumentacji `docs/`;
  nie dodano narzędzi ani zależności.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider` —
  **34 passed**. To kontrola bieżącej bazy testów; nie stanowi walidacji
  dokumentów DEMO ani XSD.
- Status repozytorium wskazuje `src/render_doc/__pycache__/` jako nieśledzony.
  Katalog nie jest ignorowany przez Git; pozostawiono istniejące lokalne `.pyc`
  bez zmian i bez dodawania ich do repozytorium.
- Nie wykonano operacji KSeF, połączeń sieciowych z KSeF, zapisów do Optimy ani
  modyfikacji `ksef2-test-client`.
- Nie przetestowano proponowanego renderu po zmianach, bo audyt nie wdraża
  implementacji. Wierność układu HTML, semantyczna zgodność wszystkich
  wariantów FA(3) i pełna walidacja XSD pozostają poza zakresem.

## Źródła

- [MF: Broszura informacyjna dotycząca struktury logicznej FA(3), marzec 2026](https://ksef.podatki.gov.pl/media/jknpcymf/broszura-informacyjna-dotyczaca-struktury-logicznej-fa-3-04032026.pdf).
- [CRWDE: wzór FA(3), schemat produkcyjny](https://crd.gov.pl/wzor/2025/06/25/13775/).
- Lokalny stan referencyjny: `src/render_doc/renderer.py`,
  `tests/test_renderer.py`, `README.md`, `docs/uzycie.md` oraz
  `docs/audyt_jakosci_fa3_html.md`.
