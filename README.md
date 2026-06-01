# 🚀 UniversalTask (utask) v2.0 - Elite Edition

`utask` ist eine hochperformante, asynchrone CLI & TUI App zur Synchronisation von Aufgaben zwischen **Apple Reminders**, **Google Tasks** und **Microsoft To Do**. Entwickelt für Power-User, die absolute Kontrolle über ihre Tasks benötigen, ohne den Terminal-Fokus zu verlieren.

---

## 🛠️ Installation & Setup

### 1. Gnadenloses Setup
Nach dem Klonen des Repos einfach das Setup-Skript ausführen. Es bereinigt alte Umgebungen und installiert alle Abhängigkeiten (Python 3.10+ erforderlich).
```bash
./setup.sh
```

### 2. Globaler Befehl
Das Setup erstellt einen Wrapper in `~/.local/bin/utask`. Stelle sicher, dass dieser Pfad in deinem `$PATH` ist (z.B. in deiner `.zshrc` oder `.bash_profile`).

---

## 🛰️ Hintergrund-Daemon (`utaskd`)

`utask` läuft "Headless". Die Sync-Engine arbeitet unsichtbar im Hintergrund, damit das UI niemals blockiert.

*   **`utask daemon-start`**: Installiert utask als macOS `LaunchAgent`. Der Sync läuft ab jetzt vollautomatisch im Hintergrund.
*   **`utask daemon-stop`**: Stoppt den Hintergrunddienst und entfernt ihn aus dem System.
*   **`utask logs`**: Zeigt die letzten Aktivitäten und den Status des Hintergrund-Syncs an.

---

## 🔄 Cross-Device Sync (iCloud Integration)

`utask` unterstützt die Synchronisation deiner Account-Konfiguration über mehrere Macs hinweg.
### 1. Shared Config aktivieren
Verschiebe deine Provider-Liste in den iCloud Drive (oder einen anderen Cloud-Ordner), um auf allen Geräten dieselben Listen zu sehen:
```bash
utask config set-shared "~/Library/Mobile Documents/com~apple~CloudDocs/utask"
```

### 2. Quick Guide: Sync auf einem neuen Mac
Wenn du utask auf einem weiteren Mac (z.B. Mac Studio oder MacBook) einrichtest:
1.  **Repo klonen & Setup:** `git clone ...` und `./setup.sh` ausführen.
2.  **Shared Path setzen:** Führe den obigen `set-shared` Befehl mit demselben Pfad aus.
3.  **Verifizieren:** `utask config show` (Der Pfad muss auf deinen iCloud-Ordner zeigen).
4.  **Erster Sync:** `utask sync` (Erkennt automatisch alle Provider aus der Cloud).

*Hinweis: Deine Passwörter/Tokens werden sicher über den **iCloud Schlüsselbund** synchronisiert.*

---

### 2. Funktionsweise
*   **`providers.json`**: Wird im Shared Directory gespeichert und hält deine Accounts synchron.
*   **Secrets**: Deine Tokens bleiben sicher im **iCloud Schlüsselbund** (via macOS Keychain).
*   **Performance**: Die lokale SQLite-Datenbank bleibt auf jedem Gerät individuell für maximale Geschwindigkeit.

---

## 🔑 Authentifizierung

Füge deine Accounts mit individuellen Labels hinzu:

*   **Google Tasks**: `utask auth-google --label "Privat"` (Folge den Anweisungen im Terminal).
*   **Microsoft To Do**: `utask auth-microsoft --client-id "DEINE_ID" --label "Arbeit"`.
*   **Apple Reminders**: Wird auf macOS automatisch erkannt.

### Verbindung erneuern (Re-Authorization)
Sollte ein Provider nicht mehr synchronisieren (z.B. Fehler `invalid_grant` im Log), muss die Verbindung neu autorisiert werden. Führe dazu einfach den ursprünglichen Auth-Befehl mit demselben Label erneut aus:

```bash
# Beispiel für Google Re-Auth
utask auth-google --label "Google"
```
**Hinweis:** Dank der integrierten **Safety-Sync** Logik bleiben deine lokalen Aufgaben bei Authentifizierungsfehlern erhalten und werden nicht gelöscht.

---

## ⌨️ TUI Steuerung (Elite Interface)

Starte das Interface mit: `utask ui`

### Navigation & Listen
*   **Sidebar (Links)**: Listen sind nach Provider und Label gruppiert.
*   **`j` / `k` oder Pfeiltasten**: Durch den Baum navigieren.
*   **`ENTER`**: Liste auswählen und Aufgaben laden.
*   **`TAB`**: Wechseln zwischen Sidebar, Aufgabenliste und Details.

### Aufgaben-Aktionen
*   **`SPACE`**: Aufgabe erledigen / wieder öffnen.
*   **`a`**: Schnelles Hinzufügen einer neuen Aufgabe.
*   **`d`**: Markierte Aufgabe löschen.
*   **`u`**: Letzte Löschung rückgängig machen (Undo-Stack).
*   **`/`**: **Globale Fuzzy-Search** – Suche über alle Listen und Provider hinweg.
*   **`p`**: **Focus Mode (Pomodoro)** – 25min Zen-Timer für den aktuellen Task.
*   **`i`**: **Insights** – Produktivitäts-Statistiken anzeigen.
*   **`v`**: **Visual Mode** – Mehrere Tasks markieren für Bulk-Actions:
    *   **`SPACE`**: Alle markierten erledigen.
    *   **`d`**: Alle markierten löschen.
    *   **`S`**: Alle markierten auf "Morgen" verschieben (Postpone).
*   **`:`**: **Command Bar** – Profi-Befehle:
    *   `:theme <flavor>` (Mocha, Macchiato, Frappe, Latte)
    *   `:recur <freq>` (daily, weekly, monthly, none)
    *   `:template add "Name" "Title" "Desc"` (Eigene Vorlagen erstellen)
    *   `:use "Name"` (Aufgabe aus Vorlage in aktueller Liste erstellen)
    *   `:create list "Name" [Provider]`
    *   `:move <Label>` (Task zu anderem Provider schieben)
    *   `:log` (Sync-Historie & Konflikte anzeigen)

### Arbeiten mit Templates (Pro-Workflow)
Templates erlauben dir, komplexere Aufgabenstrukturen vorzubereiten und sie mit einem kurzen Befehl überall einzufügen:
1. **Vorlage erstellen:** `:template add "dev" "Code Review" "Review PRs and merge to main"`
2. **Vorlage nutzen:** In eine Liste navigieren (z.B. Google Tasks) und `:use "dev"` eingeben. utask erstellt sofort den Task inkl. Beschreibung in dieser Liste.

---

## 🏥 System-Diagnose

Wenn etwas nicht rund läuft oder du einen neuen Mac einrichtest, hilft der Doctor-Befehl:

```bash
utask doctor
```
Er prüft Schreibrechte, die Erreichbarkeit deines iCloud-Pfads, den Status des Hintergrund-Daemons und die Gültigkeit deiner API-Tokens.

---

## ⚡ Natural Language Parsing (NLP)

Füge Aufgaben direkt aus dem Terminal mit menschlicher Sprache hinzu:

```bash
utask add "Meeting mit Projektgruppe nächsten Dienstag 14:00"
```

*   **Intelligenz**: Erkennt automatisch Daten wie "morgen", "nächsten Freitag", "in 2 weeks".
* **Automatische Zuordnung**: Nutzt das Label im Listennamen (z.B. `[Apple] Reminders`).

---

## 🏎️ Raycast Integration

utask bietet fertige Script-Commands für Raycast, um Aufgaben blitzschnell ohne Terminal-Fokus zu verwalten.

### 1. Einrichtung in Raycast
1. Öffne die Raycast Einstellungen -> **Extensions** -> **Scripts**.
2. Klicke auf **Add Directories** und wähle den Ordner `Raycast` in diesem Repository aus.

### 2. Verfügbare Befehle
*   **Add Task**: Tippe `add`, gib deine Aufgabe ein (z.B. `Pizza essen morgen 20:00`) und drücke Enter.
*   **View Today's Tasks**: Zeigt dir sofort eine Liste aller Aufgaben an, die heute fällig sind.

---

## 🌐 Landing Page

Besuche unsere offizielle Landing Page für einen visuellen Überblick der Features:
👉 [utask.sh](https://utask.sh) (Source in `/website`)

---

## 🔐 Security


*   **Keine Passwörter in Plaintext**: Alle Secrets werden sicher im **macOS Schlüsselbund (Keyring)** gespeichert.
*   **Privacy First**: Deine Daten gehören dir. Es gibt keinen utask-Server; der Sync erfolgt direkt zwischen deinem Mac und den Provider-APIs.

---

## 📜 System-Mantra
"Nice Data, No bloat, System-Integrity."
