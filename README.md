# 🎯 UniversalTask CLI (`utask`)

`utask` ist ein leistungsstarkes und dennoch einfaches Kommandozeilen-Tool (CLI), mit dem du deine Aufgaben und Erinnerungen nahtlos zwischen **Apple Reminders**, **Google Tasks** und deinem lokalen Terminal synchronisieren kannst.

Das Tool bietet sowohl eine schnelle Befehlszeile als auch ein **interaktives Terminal-Interface (TUI)** für flüssiges Arbeiten ohne Latenz.

---

## 📖 Inhaltsverzeichnis
1. [Installation](#-installation)
2. [Das interaktive Interface (UI)](#-das-interaktive-terminal-interface-ui)
3. [💡 Hilfe-Navigation](#-hilfe-navigation)
4. [⌨️ Steuerung & Shortcuts](#-steuerung--shortcuts)
5. [⚡ Vi-Kommandozeile (Pro-Modus)](#-vi-kommandozeile-pro-modus)
6. [🔄 Synchronisierung & Cloud-Setup](#-synchronisierung--cloud-setup)
7. [🚀 Schnelle Befehle (CLI-Modus)](#-schnelle-befehle-cli-modus)

---

## 🛠️ Installation

Stelle sicher, dass Python 3.10 oder höher installiert ist.

```bash
cd TaskSync
pip install -e .
```

---

## 🖥️ Das interaktive Terminal-Interface (UI)

Der UI-Modus ist auf maximale Geschwindigkeit optimiert. Alle Änderungen werden **sofort** lokal angezeigt, während der Sync unsichtbar im Hintergrund läuft.

```bash
utask ui
```

---

## 💡 Hilfe-Navigation
Befehl **`:help`** innerhalb der App:
- **Tab:** Wechselt zwischen Inhaltsverzeichnis (links) und Text (rechts).
- **Pfeiltasten (↑/↓):** Navigiert durch die Auswahl oder den Text.
- **Enter:** Springt im Text zum ausgewählten Abschnitt.
- **j / k:** Scrollt den Text zeilenweise.
- **Bild-Auf / Bild-Ab:** Scrollt den Text seitenweise.
- **Esc / q:** Schließt die Hilfe.

---

## ⌨️ Steuerung & Shortcuts
- **Navigation:** `j` / `k` (oder Pfeiltasten) zum Scrollen.
- **Listenwechsel:** `Tab`, um zwischen Listen (links) und Aufgaben (rechts) zu wechseln.
- **Abhaken:** `Leertaste (Space)`, um eine Aufgabe zu erledigen.
- **Hinzufügen:** `a` (Add) drücken und Titel eintippen.
- **Umbenennen:** `r` (Rename) drücken.
- **Löschen:** `d` (Delete) drücken.
- **Suchen:** `/` (Search) filtert die Liste live.
- **Synchronisieren:** `s` (Sync) stößt manuellen Abgleich an.
- **Beenden:** `q` (Quit).

---

## ⚡ Vi-Kommandozeile (Pro-Modus)
Drücke **`:`**, um Befehle einzugeben:
- **`:create list "Name"`**: Erstellt eine neue Liste.
- **`:delete list "Name"`**: Löscht eine Liste.
- **`:sort alpha`** | **`:sort status`**: Ändert die Sortierung.
- **`:auth google`**: Startet die Google Tasks Einrichtung.
- **`:help`**: Öffnet diese Dokumentation.
- **`:q`**: Beendet das Programm.

---

## 🔄 Synchronisierung & Cloud-Setup

### Apple Reminders (macOS)
Erfordert keine Einrichtung. Bestätige beim ersten Start einfach den macOS-Zugriffsdialog.

### Google Tasks (3-Minuten Einrichtung)
Google hat das Interface auf die **Google Auth Platform** aktualisiert. Folge diesen Schritten:

1. **Projekt:** Gehe zur [Google Cloud Console](https://console.cloud.google.com/). Klicke oben auf "New Project" (z.B. "utask-sync").
2. **API:** Suche oben nach **"Google Tasks API"** und klicke auf **Enable**.
3. **Google Auth Platform (Einrichtung):**
   - Gehe links zu **APIs & Services** -> **Google Auth Platform**.
   - **Branding:** Klicke "Get Started". Gib App-Namen und deine E-Mail an. "Save".
   - **Audience:** Wähle **External**. Scrolle zu **Test users** -> **+ ADD USERS** und füge deine E-Mail (`gerwin.weiher@gmail.com`) hinzu. **WICHTIG:** Ohne diesen Schritt kommt Fehler 403!
   - **Data Access:** Klicke "Add Scopes" -> Suche nach `tasks` -> Wähle `.../auth/tasks` -> "Save".
4. **Anmeldedaten:**
   - Gehe links zu **Credentials** -> **+ Create Credentials** -> **OAuth client ID**.
   - Application type: **Desktop app**. Name: "utask" -> "Create".
   - Klicke im Fenster auf **DOWNLOAD JSON**.
5. **Aktivierung:**
   - Gib in der App **`:auth google`** ein.
   - Kopiere den Text aus der JSON-Datei hinein und drücke **STRG+S**. 
   - Der Browser öffnet sich zum Login. Fertig!

### Microsoft To Do (2-Minuten Einrichtung)
1. Gehe zum [Azure Portal](https://portal.azure.com/).
2. Suche oben in der Leiste nach **"App-Registrierungen"** (App registrations).
3. Klicke auf **+ Neue Registrierung**. Name: "utask-cli".
4. Wähle: **"Konten in einem beliebigen Organisationsverzeichnis und persönliche Microsoft-Konten"** (Multitenant).
5. Klicke auf **Registrieren**.
6. Kopiere die **Anwendungs-ID (Client)**.
7. Gib in der App **`:auth microsoft`** ein, füge die ID ein und folge den Anweisungen.

---

## 📱 Mobile Nutzung
Änderungen werden sofort mit deinem iPhone oder Android-Handy synchronisiert.
