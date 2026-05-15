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
*   **`/`**: Schnellsuche (Fuzzy-Filter für die aktuelle Liste).

---

## ⚡ Natural Language Parsing (NLP)

Füge Aufgaben direkt aus dem Terminal mit menschlicher Sprache hinzu:

```bash
utask add "Meeting mit Projektgruppe nächsten Dienstag 14:00"
```

*   **Intelligenz**: Erkennt automatisch Daten wie "morgen", "nächsten Freitag", "in 2 weeks".
*   **Automatische Zuordnung**: Nutzt das Label im Listennamen (z.B. `[Apple] Reminders`).

---

## 🔐 Security

*   **Keine Passwörter in Plaintext**: Alle Secrets werden sicher im **macOS Schlüsselbund (Keyring)** gespeichert.
*   **Privacy First**: Deine Daten gehören dir. Es gibt keinen utask-Server; der Sync erfolgt direkt zwischen deinem Mac und den Provider-APIs.

---

## 📜 System-Mantra
"Nice Data, No bloat, System-Integrity."
