# Glossar (Deutsch)

Diese Begriffe konsistent verwenden — die Oberfläche selbst ist auf
Englisch, du übersetzt sinngemäß, wenn auf Deutsch geantwortet wird. Der
englische Fachbegriff steht in Klammern, da er in JSON-Feldnamen und in
der UI so vorkommt.

- **Mitglied** (Member): eine Lehrkraft, die an der Fahrgemeinschaft
  teilnimmt.
- **Fahrplan** (Driving Plan): der komplette Zwei-Wochen-Plan ("Woche A" +
  "Woche B") der Fahrgemeinschaft, bestehend aus je einem **Tagesplan**
  pro Wochentag und Woche.
- **Tagesplan** (Day Plan): der Plan für einen einzelnen Wochentag
  innerhalb einer Woche (A oder B) — die **Partyn** für Hin- und
  Rückfahrt an diesem Tag.
- **Party**: eine Gruppe, die für eine Fahrtrichtung
  an einem Tag zusammen fährt: eine **Fahrerin/ein Fahrer** (Driver) plus
  null oder mehr **Mitfahrende** (Passengers).
- **Fahrer/Fahrerin** (Driver): die Person, die für eine bestimmte
  Party fährt.
- **Mitfahrer/Mitfahrerin** (Passenger): eine Person, die bei einer
  Party mitfährt. Dieselbe Person kann an einem Tag auf dem Hinweg
  fahren und auf dem Rückweg mitfahren (oder umgekehrt), aber nie beides
  für dieselbe Fahrtrichtung.
- **Mandatory Driver** (`isDesignatedDriver`): jemand,
  der an einem Tag zwangsläufig selbst fahren muss, weil niemand sonst zu
  einer passenden Zeit ankommt/losfährt — in der UI mit Flaggen-Symbol
  markiert.
- **Solo Driver** (`isLonelyDriver`): eine
  Fahrerin/ein Fahrer, deren/dessen Party für diese Fahrtrichtung
  keine Mitfahrenden haben darf (durch "Skip AM"/"Skip PM").
- **Hinweg** (Schoolbound): die morgendliche Fahrt zur Schule.
- **Rückweg** (Homebound): die Fahrt nach Schulschluss nach Hause.
- **Woche A / Woche B** (Week A / Week B): die zwei Wochen des Rotationszyklus.
- **Custom Prefs** (Custom Day / Custom Preferences):
  personenbezogene Ausnahmen vom stundenplanbasierten Zeitplan an
  einzelnen Tagen. Optionen: **Skip** (an diesem Tag komplett ausgenommen),
  **Needs Car** (muss selbst fahren), **Skip AM** / **Skip PM**
  (Einzelfahrer/in für diese Fahrtrichtung, impliziert Needs Car), **No
  Wait PM** (die Rückweg-Party muss exakt zur Feierabendzeit dieser
  Person fahren, keine Toleranz).
- **Zeittoleranz** (Time Tolerance): das standardmäßige 30-Minuten-Fenster,
  innerhalb dessen Mitglieder mit ähnlichen (nicht identischen) Zeiten in
  dieselbe Party einsortiert werden.
- **Algorithmus-Phase** (Algorithm Phase): der Erstellungsschritt, der eine
  Party angelegt oder verändert hat — Phase 2 (initiale
  Fahrerauswahl), Phase 3 (Ausgleich von Personen, die zu oft fahren),
  Phase 4 (zusätzliche Fahrer zur Entlastung überfüllter Partyn).
- **Stundenplan** (Timetable): die aus WebUntis abgeleiteten Ankunfts-/
  Feierabendzeiten einer Person, vor Anwendung individueller
  Tagespräferenzen.
