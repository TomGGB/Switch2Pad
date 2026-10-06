<div align="center">

<img src="../assets/icon.png" width="112" alt="Switch2Pad">

# Switch2Pad

**Nutze deinen Nintendo Switch 2 Pro Controller am PC als Xbox-360- oder DualShock-4-Controller – mit Gyroskop, Touchpad-Gesten und Vibration.**

[![Release](https://img.shields.io/github/v/release/TomGGB/Switch2Pad?label=download&color=e60012)](https://github.com/TomGGB/Switch2Pad/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/TomGGB/Switch2Pad/total?color=e60012)](https://github.com/TomGGB/Switch2Pad/releases)
![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078d4)
![Linux](https://img.shields.io/badge/Linux-x86__64-f7a41d)

[English](../README.md) · [Español](README.es.md) · [Português](README.pt-BR.md) · [Français](README.fr.md) · **Deutsch** · [Italiano](README.it.md) · [日本語](README.ja.md) · [简体中文](README.zh-CN.md)

<img src="screenshots/main.png" width="820" alt="Switch2Pad">

</div>

## Warum Switch2Pad?

Windows und die meisten Spiele verstehen den Switch 2 Pro Controller per USB nicht: Er sendet nicht einmal Daten, bevor er eine spezielle Initialisierungssequenz erhält. Switch2Pad spricht direkt mit dem Controller und macht daraus einen **virtuellen Xbox 360 oder DualShock 4**, den jedes Spiel, jeder Emulator und jeder Launcher unterstützt.

- 🎮 **Xbox-360- oder PS4-Modus** – jederzeit umschaltbar, sogar im Spiel.
- 🌀 **Gyroskop und Beschleunigungssensor** (PS4-Modus) – Bewegungssteuerung in Spielen und Emulatoren mit DS4-Unterstützung.
- ✌️ **Touchpad-Gesten, auch mit zwei Fingern** – halte *Aufnahme* gedrückt und die Sticks werden zu Fingern; das Steuerkreuz wischt schnell, L3/R3 klicken links/rechts.
- 📳 **Vibration** vom Spiel an den Controller.
- 🧊 **Live-3D-Controller**, der dem Gyroskop des echten Controllers folgt und gedrückte Tasten hervorhebt.
- 🚫 **Vorrang vor Steam** – mit einem Klick übernimmt Steam den Controller nicht mehr.
- 🔧 **Alle Tasten neu belegen**, A/B/X/Y nach Position oder Buchstabe, Stick-Totzone.
- 🪟 **Natives Windows-11-Design** (Mica, hell/dunkel, Akzentfarbe), Infobereich und Autostart.
- 🌍 **7 Sprachen** und 🐧 **Windows und Linux**.

## Download

| Plattform | Datei | Hinweise |
|---|---|---|
| **Windows 10/11** | [`Switch2Pad.exe`](https://github.com/TomGGB/Switch2Pad/releases/latest) | Keine Installation. Fehlt [ViGEmBus](https://github.com/nefarius/ViGEmBus/releases), bietet die App die Installation an. |
| **Linux x86_64** | [`Switch2Pad-<version>-linux-x86_64.tar.gz`](https://github.com/TomGGB/Switch2Pad/releases/latest) | Entpacken und `./install.sh` ausführen (Menüeintrag und udev-Regeln). |

## Schnellstart

1. Schließe den Switch 2 Pro Controller per **USB-C-Kabel** an.
2. Öffne Switch2Pad und wähle **Xbox 360** oder **PS4 · DualShock 4**.
3. Spielen. Beim Schließen des Fensters läuft die App im Infobereich weiter.

> **Du nutzt Steam?** Öffne den Tab *Steam* und klicke auf **Switch2Pad Vorrang geben**, damit Steam den Controller nicht mehr übernimmt (Steam startet von selbst neu; eine Sicherung der Konfiguration wird angelegt).

## Screenshots

| Touchpad-Gesten und Hintergrund | Tastenbelegung |
|---|---|
| <img src="screenshots/touchpad.png" alt=""> | <img src="screenshots/buttons.png" alt=""> |
| **Vorrang vor Steam** | **Helles Design · Xbox-Modus** |
| <img src="screenshots/steam.png" alt=""> | <img src="screenshots/light-xbox.png" alt=""> |
| **Übersetzte Oberfläche (日本語)** | **Infobereich** |
| <img src="screenshots/japanese.png" alt=""> | <img src="screenshots/tray.png" width="260" alt=""> |

## Touchpad-Gesten (PS4-Modus)

Halte die dem Touchpad zugewiesene Taste (standardmäßig **Aufnahme**) gedrückt und:

| Eingabe | Touchpad-Aktion |
|---|---|
| Rechter / linker Stick | Finger 1 / Finger 2 – bewege beide für **Zwei-Finger-Gesten** (z. B. „MOVE CAR“ in *inFAMOUS Second Son*) |
| Steuerkreuz | Schnelles Wischen in diese Richtung (mit ZL oder ZR mit zwei Fingern) |
| L3 / R3 | Finger links / rechts **+ Klick** (beide = zwei Finger + Klick) |
| Controller drehen | Zieht einen Finger mit dem Gyroskop (optional) |
| Kurzes Tippen der Taste | Klick |

Solange die Touchpad-Taste gehalten wird, gehen Sticks und Steuerkreuz nicht an das Spiel.

## FAQ

<details><summary><b>Funktioniert es per Bluetooth?</b></summary>
Noch nicht – nur USB.
</details>

<details><summary><b>Welchen Modus soll ich nutzen, Xbox oder PS4?</b></summary>
Xbox 360 funktioniert mit fast allen PC-Spielen. Nutze PS4 für Gyroskop oder Touchpad (PS4-Emulatoren wie shadPS4, Spiele mit DS4-Unterstützung, Steam).
</details>

<details><summary><b>Ein Spiel sieht zwei Controller.</b></summary>
Verstecke den physischen Controller mit <a href="https://github.com/nefarius/HidHide">HidHide</a> oder aktiviere <i>Vorrang vor Steam</i>, wenn der zweite von Steam Input kommt.
</details>

<details><summary><b>Braucht es Administratorrechte?</b></summary>
Die App läuft als normaler Benutzer. Nur die Installation von ViGEmBus (Windows) oder der udev-Regeln (Linux) fragt einmalig danach.
</details>

<details><summary><b>Welche Controller werden unterstützt?</b></summary>
Switch 2 Pro Controller (getestet). NSO-GameCube-Controller: experimentell. Joy-Con 2: noch nicht.
</details>

## Aus dem Quellcode bauen

```sh
pip install -r requirements.txt pyinstaller
python -m PyInstaller switch2pad.spec      # Windows -> dist/Switch2Pad.exe
sh build_linux.sh                           # Linux   -> dist/Switch2Pad-<version>-linux-x86_64.tar.gz
```

## Mitmachen

Issues, Ideen, Übersetzungen und Pull Requests sind willkommen – siehe [CONTRIBUTING.md](../CONTRIBUTING.md). Wenn dir Switch2Pad hilft, **hilft ein ⭐ anderen, es zu finden.**

---

<sub>Switch2Pad ist ein unabhängiges Projekt und steht in keiner Verbindung zu Nintendo, Sony, Microsoft oder Valve. Nintendo Switch, DualShock, Xbox und Steam sind Marken ihrer jeweiligen Inhaber.</sub>
