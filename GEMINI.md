# 🚀 Master-Konzept: UniversalTask (utask) v2.0

## 1. Architektur, Security & Tech-Stack (Headless Core)

Das UI und die Sync-Logik werden radikal entkoppelt, um absolute System-Integrität und Performance zu garantieren.

* **TUI-Framework:** **Textual** (Python). Unterstützt echtes CSS, asynchrones Rendering und Grid-Layouts.
* **CLI-Framework:** **Typer**. Perfekt für blitzschnelles Argument-Parsing.
* **Hintergrund-Daemon (`utaskd`):** Die Sync-Engine läuft als unsichtbarer, asynchroner Hintergrundprozess. Das TUI blockiert nie, die Latenz beim Tippen liegt bei null.
* **Datenbank (Local Single Source of Truth):** **SQLModel (SQLite)**. Das TUI kommuniziert ausschließlich mit der lokalen Datenbank.
* **Wasserdichtes Konflikt-Management:** "Latest Write Wins" mit ISO-Timestamps. Verhindert Datenkorruption zwischen lokaler CLI-Änderung und parallelem Handy-Edit.
* **Keychain-Integration (Security):** Tokens (Google/Microsoft) werden nicht mehr als rohe `.json` oder `pickle`-Dateien gespeichert. Die Bibliothek `keyring` legt sie verschlüsselt und nativ im macOS Schlüsselbund (oder Linux Secret Service) ab.
* **Shared Config (Cross-Device Sync):** Die Provider-Konfiguration (`providers.json`) kann via `utask config set-shared` in den iCloud Drive verschoben werden. Dadurch haben alle Macs denselben Stand an aktiven Accounts, während die SQLite-Datenbank und die Secrets (via iCloud Keychain) sicher und performant bleiben.

---

## 2. Visuelles Design & Layout (Redesign)

Die neue Oberfläche ist an professionelle Dashboards (wie `tiptop`) angelehnt.

### Das Catppuccin (Mocha) Farbschema

Zentral über `.tcss`-Dateien definiert:

* **Hintergrund (`Base`):** `#1e1e2e` (Tiefdunkelblau/Grau)
* **Panels (`Mantle`):** `#181825` (Etwas dunkler für Container)
* **Akzent (`Mauve`):** `#cba6f7` (Lila für aktive Tabs/Auswahl)
* **Erledigt (`Green`):** `#a6e3a1` (Sanftes Grün)
* **Warnung/Löschen (`Red`):** `#f38ba8` (Sanftes Rot)

### Zukünftiges UI-Layout (Grid mit Sparklines)

```text
┌─────────────────────────────────────────────────────────────┐
│ 🚀 utask v2.0          [ ▂▃▅▆▇ ] 42 Done  [ 🟢 Sync OK ]    │
├──────────────┬───────────────────────────────┬──────────────┤
│ 📂 LISTEN    │ 📝 AUFGABEN (Google Tasks)    │ ℹ️ DETAILS   │
│ ──────────── │ ───────────────────────────── │ ──────────── │
│ > Privat     │ ◯ Katze füttern               │ Fällig:      │
│   Arbeit     │ ◯ Server updaten              │ Heute, 18:00 │
│   Einkauf    │ ◯ Meeting vorbereiten         │              │
│              │                               │ Provider:    │
│ 📓 NOTIZEN   │                               │ Google       │
│ ──────────── │                               │              │
│   Ideen      │                               │ Notizen:     │
│   Projekte   │                               │ [Leer]       │
├──────────────┴───────────────────────────────┴──────────────┤
│ : Befehl eingeben...   (TAB wechseln | a Neu | SPACE Check) │
└─────────────────────────────────────────────────────────────┘

```

---

## 3. Feature-Set & Power-User Workflow

Die Steuerung ist komplett auf Keyboard und Muscle-Memory ausgelegt.

* **Vim-Motions & Bulk Actions:** `j/k` für Navigation, `dd` zum Löschen. Visual Mode (`v`) erlaubt das Markieren mehrerer Tasks, um sie mit einem Tastendruck zu verschieben oder abzuarbeiten.
* **Fuzzy Finding (`/`):** Fehlerverzeihende Suche (wie `fzf`), die über alle Provider hinweg Tasks in Millisekunden findet.
* **Undo/Redo-Stack (`u`):** Lokale Änderungen können sofort rückgängig gemacht werden, bevor der Daemon sie verarbeitet.
* **Natural Language Processing:** Der CLI-Befehl `utask add "Meeting mit Agentur morgen 15:00"` parst Datum und Uhrzeit lokal und wandelt sie in das richtige ISO-Format um.
* **System-Integration (Spotlight/Raycast):** Globale Shortcuts (`Cmd + Space`), um via Bash-Wrapper direkt Tasks in die Engine zu schießen, ohne das Terminalfenster zu öffnen.
* **Markdown Export:** `utask export md` zieht einen kompletten Dump aller Listen als sauberes Markdown-File (inklusive Checkboxen `- [ ]`).

---

## 4. Resilience, Telemetrie & Logging (Operations)

Der Daemon (`utaskd`) ist darauf ausgelegt, niemals abzustürzen, selbst wenn das Netzwerk komplett ausfällt.

* **Exponential Backoff:** Bei API-Rate-Limits oder Server-Timeouts von Google/Microsoft wartet der Daemon intelligent (1, 2, 4, 8 Minuten), bevor er den Sync erneut versucht.
* **Dead Letter Queue (DLQ):** Korrupte Tasks, die absolut nicht hochgeladen werden können, blockieren nicht den Loop. Sie landen in einer lokalen Fehler-Tabelle und werden im TUI mit ⚠️ markiert, damit sie manuell bereinigt werden können.
* **Log-Rotation & CLI-Diagnose:** Der Daemon schreibt ein isoliertes Logfile (`~/.config/utask/daemon.log`), das automatisch in der Größe limitiert wird. Der Befehl `utask logs` gibt dir die Systemgesundheit und Sync-Historie formatiert im Terminal aus.

---

## 5. Packaging, Distribution & CI/CD (Der Installer)

Dies ist der wichtigste Schritt, um `utask` von einem reinen Python-Skript in ein professionelles, isoliertes CLI-Tool zu verwandeln.

* **Standalone Binaries (PyInstaller / Nuitka):** Die App wird in eine einzige, in sich geschlossene Binary kompiliert. Dadurch muss der Endnutzer sich nicht um Python-Versionen, Virtual Environments (`.venv`) oder kollidierende Dependencies kümmern. Das Tool startet sofort und ohne Overhead.
* **Homebrew Tap (macOS Installer):** Ein eigenes Repository (`aeon022/homebrew-tap`), das die Installation zum absoluten Standard macht. Mit einem einfachen `brew install aeon022/tap/utask` wird das Tool samt Daemon-Konfiguration (via macOS `launchd`) installiert. Update-Runs laufen danach simpel über `brew upgrade`.
* **Pipx Fallback (Linux / Cross-Platform):** Für Umgebungen ohne Homebrew wird die App via `pipx install utask` verteilt. Das installiert die CLI isoliert im Systempfad, ohne die globalen Python-Pakete zu verpesten.
* **CI/CD (GitHub Actions):** Jedes Release auf GitHub stößt eine Pipeline an. Diese führt automatisierte API-Mock-Tests durch und baut danach automatisch die fertigen macOS/Linux-Binaries und aktualisiert das Homebrew-Tap.

---

## 6. Implementierungs-Roadmap

**Phase 1: Headless Core, Daemon & Security**

1. Sync-Routinen in asynchrone Funktionen (`aiosqlite`, `aiohttp`) umschreiben.
2. Auskopplung der Engine in den Hintergrund-Prozess (`utaskd`).
3. Integration von `keyring` für verschlüsselte Token-Speicherung im Schlüsselbund.

**Phase 2: TUI-Redesign & Catppuccin**

1. Trennung von UI-Logik und Styling (`.tcss` Dateien) und Aufbau des Catppuccin-Themes.
2. Konstruktion des starren 3-Spalten-Grids und der Header-Sparklines.

**Phase 3: Power-User Features**

1. Implementierung der Vim-Motions, Bulk-Actions und des lokalen Undo-Stacks.
2. Integration der Fuzzy-Search-Engine.
3. Aufbau der lokalen Logging-Rotation und des `utask logs`-Befehls.

**Phase 4: CLI & macOS System-Integration**

1. NLP-Parser (`dateparser`) an Typer-CLI anbinden.
2. Markdown-Export-Helfer implementieren.
3. Bash-Wrapper für Raycast und Apple Shortcuts schreiben.

**Phase 5: Packaging & Distribution (Installer)**

1. `PyInstaller`/`Nuitka`-Spec-Files konfigurieren, um saubere Binaries zu kompilieren.
2. Erstellen des GitHub Actions Workflows für automatische Tests und Builds.
3. Aufsetzen des Homebrew Taps (Formula erstellen) für das finale `brew install` Erlebnis.
