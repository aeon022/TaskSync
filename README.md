# 🎯 UniversalTask CLI (`utask`)

`utask` ist ein leistungsstarkes und dennoch einfaches Kommandozeilen-Tool (CLI), mit dem du deine Aufgaben und Erinnerungen nahtlos zwischen **Apple Reminders**, **Google Tasks** und deinem lokalen Terminal synchronisieren kannst.

Das Tool bietet sowohl eine schnelle Befehlszeile als auch ein **interaktives Terminal-Interface (TUI)** für flüssiges Arbeiten ohne Latenz.

---

## 💡 Hilfe-Navigation
Wenn du diese Hilfe innerhalb der App aufrufst (Befehl `:help`), kannst du sie wie folgt bedienen:

- **Tab:** Wechselt den Fokus zwischen dem Inhaltsverzeichnis (links) und dem Text (rechts).
- **Pfeiltasten (↑/↓):** Navigiert durch das Verzeichnis oder den Text (je nachdem, was fokussiert ist).
- **Enter:** Springt im Text direkt zum ausgewählten Abschnitt (wenn das Verzeichnis fokussiert ist).
- **j / k:** Scrollt den Text zeilenweise nach oben/unten (Vim-Style).
- **Bild-Auf / Bild-Ab:** Scrollt den Text seitenweise.
- **Esc / q:** Schließt die Hilfe-Ansicht.

---

## 📖 Inhaltsverzeichnis
1. [Installation](#-installation)
2. [Das interaktive Interface (UI)](#-das-interaktive-terminal-interface-ui)
3. [Steuerung & Shortcuts](#-steuerung--shortcuts)
4. [Vi-Kommandozeile (Pro-Modus)](#-vi-kommandozeile-pro-modus)
5. [Schnelle Befehle (CLI-Modus)](#-schnelle-befehle-cli-modus)
6. [Synchronisierung & Cloud-Setup](#-synchronisierung--cloud-setup)
7. [Mobile Nutzung](#-mobile-nutzung)

---

## 🛠️ Installation

Stelle sicher, dass Python 3.10 oder höher installiert ist.

```bash
cd TaskSync
pip install -e .
```

**Tipp:** Um das Tool einfach mit `utask` aufzurufen, erstelle einen Symlink oder stelle sicher, dass dein Python-Script-Pfad in der PATH-Variable liegt.

---

## 🖥️ Das interaktive Terminal-Interface (UI)

Der UI-Modus ist das Herzstück von `utask`. Er ist auf maximale Geschwindigkeit optimiert. Alle Änderungen (Hinzufügen, Löschen, Erledigen) werden **sofort** im UI angezeigt, während die Synchronisation mit Apple oder Google unsichtbar im Hintergrund läuft.

```bash
utask ui
```

---

## ⌨️ Steuerung & Shortcuts

In der Listen- oder Aufgabenansicht stehen dir folgende Tasten zur Verfügung:

- **Navigation:** `j` / `k` (oder Pfeiltasten) zum Scrollen.
- **Listenwechsel:** `Tab`, um zwischen der Listen-Spalte (links) und der Aufgaben-Spalte (rechts) zu wechseln.
- **Abhaken:** `Leertaste (Space)`, um eine Aufgabe zu erledigen/reaktivieren.
- **Hinzufügen:** `a` (Add), öffnet ein Eingabefeld für eine neue Aufgabe.
- **Umbenennen:** `r` (Rename), ändert den Namen der markierten Aufgabe.
- **Löschen:** `d` (Delete), entfernt die markierte Aufgabe.
- **Suchen:** `/` (Search), filtert die aktuelle Liste live während des Tippens.
- **Synchronisieren:** `s` (Sync), stößt einen manuellen Cloud-Abgleich an.
- **Beenden:** `q` (Quit).

---

## ⚡ Vi-Kommandozeile (Pro-Modus)

Drücke jederzeit **`:`**, um die Befehlszeile am unteren Rand zu öffnen (wie in Vim):

- **`:create list "Name"`**: Erstellt eine neue Liste (z. B. in Apple Reminders).
- **`:delete list "Name"`**: Löscht eine bestehende Liste unwiderruflich.
- **`:sort alpha`**: Sortiert Aufgaben alphabetisch.
- **`:sort status`**: (Standard) Sortiert nach Status (Offen -> Erledigt).
- **`:help`** oder **`:open help`**: Öffnet diese Dokumentation direkt in der App.
- **`:q`** oder **`:quit`**: Beendet das Programm.
- **`Esc`**: Bricht die Eingabe ab und kehrt zur normalen Steuerung zurück.

---

## 🚀 Schnelle Befehle (CLI-Modus)

Für schnelle Aktionen direkt in der Shell, ohne das UI zu öffnen:

### Aufgaben verwalten
- **Anzeigen:** `utask list` (offene Aufgaben) | `utask list --all` (alle).
- **Hinzufügen:** `utask add "Titel"` | `utask add "Titel" --list "Name"`.
- **Erledigen:** `utask complete <ID>`.
- **Umbenennen:** `utask rename <ID> "Neuer Name"`.
- **Löschen:** `utask delete <ID>`.

### Listen verwalten (`list-mgnt`)
- **Erstellen:** `utask list-mgnt create "Name"`.
- **Löschen:** `utask list-mgnt delete "Name"`.
- **Umbenennen:** `utask list-mgnt rename "Alt" "Neu"`.

---

## 🔄 Synchronisierung & Cloud-Setup

### Apple Reminders (macOS)
- **Automatisch:** `utask` erkennt deine Listen (z.B. "Erinnerungen").
- **Berechtigung:** Beim ersten Start musst du den Zugriff in den macOS-Systemeinstellungen erlauben.

### Google Tasks
1. Erstelle ein Projekt in der [Google Cloud Console](https://console.cloud.google.com/).
2. Aktiviere die **Google Tasks API**.
3. Erstelle **OAuth 2.0-Client-IDs** (Desktop-App) und speichere sie als `credentials.json` im Projektordner.
4. Starte `utask sync` für die Erstanmeldung.

---

## 📱 Mobile Nutzung
Änderungen im Terminal werden über die Cloud mit deinem iPhone (Apple Reminders) oder Android-Gerät (Google Tasks) synchronisiert. Was du im Terminal tippst, hast du unterwegs sofort auf dem Handy dabei!
