# 🚀 UniversalTask (utask) v2.0 - Elite Edition

`utask` ist eine hochperformante, asynchrone CLI & TUI App zur Synchronisation von Aufgaben zwischen **Apple Reminders**, **Google Tasks** und **Microsoft To Do (FH Burgenland)**.

---

## 🛠️ Installation & Setup

### 1. Gnadenloses Setup
Nach dem Klonen des Repos einfach das Setup-Skript ausführen. Es bereinigt alte Umgebungen und installiert alle Abhängigkeiten (Python 3.10+ erforderlich).
```bash
./setup.sh
```

### 2. Globaler Befehl
Das Setup erstellt einen Wrapper in `~/.local/bin/utask`. Stelle sicher, dass dieser Pfad in deinem `$PATH` ist.

---

## 🛰️ Hintergrund-Daemon (`utaskd`)

utask v2.0 läuft "Headless". Du musst dich nicht um den Sync kümmern.

*   **`utask daemon-start`**: Installiert utask als macOS `LaunchAgent`. Der Sync läuft ab jetzt alle 5 Minuten vollautomatisch im Hintergrund.
*   **`utask daemon-stop`**: Stoppt den Hintergrunddienst und entfernt ihn aus dem System.
*   **`utask logs`**: Zeigt die letzten Aktivitäten und den Status des Hintergrund-Syncs an.

---

## ⌨️ TUI Steuerung (Elite Interface)

Starte das Interface mit: `utask ui`

### Navigation & Listen
*   **Sidebar (Links)**: Listen sind nach Provider (Apple, FH, Google) gruppiert.
*   **`j` / `k` oder Pfeiltasten**: Durch den Baum navigieren.
*   **`ENTER`**: Liste auswählen und Aufgaben laden.
*   **`TAB`**: Wechseln zwischen Sidebar, Aufgabenliste und Details.

### Aufgaben-Aktionen
*   **`SPACE`**: Aufgabe erledigen / wieder öffnen (triggert sofortigen Sync-Zeitstempel).
*   **`a`**: Schnelles Hinzufügen einer neuen Aufgabe.
*   **`d`**: Markierte Aufgabe löschen.
*   **`u`**: Letzte Löschung rückgängig machen (Undo-Stack).
*   **`v`**: Visual Mode (Mehrere Aufgaben markieren).

### Befehlszeile (`:`) & Suche (`/`)
*   **`:`**: Befehlsmodus öffnen.
    *   `:sync` - Sofortigen manuellen Sync erzwingen.
    *   `:h` oder `:hide` - Erledigte Aufgaben verstecken/zeigen.
    *   `:delete list "Name"` - Eine komplette Liste überall (Remote & Lokal) löschen.
    *   `:q` - App beenden.
*   **`/`**: Schnellsuche (Fuzzy-Filter für die aktuelle Liste).
*   **`?`**: Dieses Handbuch öffnen.
*   **`ESC`**: Abbrechen / Zurück.

---

## ⚡ Natural Language Parsing (NLP)

Du kannst Aufgaben direkt aus dem Terminal mit menschlicher Sprache hinzufügen:

```bash
utask add "Meeting mit Projektgruppe nächsten Dienstag 14:00"
```

*   **Intelligenz**: Erkennt automatisch Daten wie "morgen", "nächsten Freitag", "in 2 weeks".
*   **Listen-Zuordnung**: Nutze `--list-name "Privat"`, um die Aufgabe direkt in eine spezifische Liste zu schieben.

---

## 📈 Produktivitäts-Tracking

Im Header des TUI siehst du eine **Echtzeit-Sparkline**.
*   Jeder Balken repräsentiert einen der letzten 10 Tage.
*   Die Höhe zeigt die Anzahl der an diesem Tag erledigten Aufgaben.
*   Daten kommen direkt aus der lokalen SQLite "Single Source of Truth".

---

## 🔐 Security

*   **Keine Passwörter in Plaintext**: Alle Tokens (Google/Microsoft) werden sicher im **macOS Schlüsselbund (Keyring)** gespeichert.
*   **OAuth2**: Nutzt moderne Authentifizierungs-Flows für maximale Sicherheit.

---

## 📜 System-Mantra
"Nice Data, No bloat, System-Integrity."
