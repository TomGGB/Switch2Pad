<div align="center">

<img src="../assets/icon.png" width="112" alt="Switch2Pad">

# Switch2Pad

**Usa il tuo Pro Controller Nintendo Switch 2 su PC come un controller Xbox 360 o DualShock 4, con giroscopio, gesti del touchpad e vibrazione.**

[![Release](https://img.shields.io/github/v/release/TomGGB/Switch2Pad?label=download&color=e60012)](https://github.com/TomGGB/Switch2Pad/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/TomGGB/Switch2Pad/total?color=e60012)](https://github.com/TomGGB/Switch2Pad/releases)
![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078d4)
![Linux](https://img.shields.io/badge/Linux-x86__64-f7a41d)

[English](../README.md) · [Español](README.es.md) · [Português](README.pt-BR.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · **Italiano** · [日本語](README.ja.md) · [简体中文](README.zh-CN.md)

<img src="screenshots/main.png" width="820" alt="Switch2Pad">

</div>

## Perché Switch2Pad?

Windows e la maggior parte dei giochi non riconoscono il Pro Controller di Switch 2 via USB: non invia nemmeno dati finché non riceve una sequenza di inizializzazione speciale. Switch2Pad comunica direttamente con il controller e lo trasforma in un **Xbox 360 o DualShock 4 virtuale**, supportato da qualsiasi gioco, emulatore o launcher.

- 🎮 **Modalità Xbox 360 o PS4**: cambiala quando vuoi, anche durante il gioco.
- 🌀 **Giroscopio e accelerometro** (modalità PS4): mira con il movimento in giochi ed emulatori compatibili con il DS4.
- ✌️ **Gesti del touchpad, anche a due dita**: tieni premuto *Acquisizione* e gli stick diventano dita; la croce fa scorrimenti rapidi e L3/R3 cliccano a sinistra/destra.
- 📳 **Vibrazione** inviata dal gioco al controller.
- 🧊 **Controller 3D in tempo reale** che segue il giroscopio del controller vero e illumina i pulsanti premuti.
- 🚫 **Priorità su Steam**: con un clic Steam smette di prendere e rimappare il controller.
- 🔧 **Rimappatura di tutti i pulsanti**, A/B/X/Y per posizione o per lettera, zona morta degli stick.
- 🪟 **Aspetto nativo di Windows 11** (Mica, chiaro/scuro, colore principale), area di notifica e avvio con Windows.
- 🌍 **7 lingue** e 🐧 **Windows e Linux**.

## Download

| Piattaforma | File | Note |
|---|---|---|
| **Windows 10/11** | [`Switch2Pad.exe`](https://github.com/TomGGB/Switch2Pad/releases/latest) | Nessuna installazione. Se manca [ViGEmBus](https://github.com/nefarius/ViGEmBus/releases), l'app propone di installarlo. |
| **Linux x86_64** | [`Switch2Pad-<version>-linux-x86_64.tar.gz`](https://github.com/TomGGB/Switch2Pad/releases/latest) | Estrai ed esegui `./install.sh` (aggiunge la voce di menu e le regole udev). |

## Avvio rapido

1. Collega il Pro Controller di Switch 2 con un **cavo USB-C**.
2. Apri Switch2Pad e scegli **Xbox 360** o **PS4 · DualShock 4**.
3. Gioca. Chiudendo la finestra resta attivo nell'area di notifica.

> **Usi Steam?** Apri la scheda *Steam* e clicca **Dai la priorità a Switch2Pad** perché Steam non prenda più il controller (Steam si riavvia da solo; viene salvato un backup della configurazione).

## Screenshot

| Gesti del touchpad e background | Rimappatura dei pulsanti |
|---|---|
| <img src="screenshots/touchpad.png" alt=""> | <img src="screenshots/buttons.png" alt=""> |
| **Priorità su Steam** | **Tema chiaro · modalità Xbox** |
| <img src="screenshots/steam.png" alt=""> | <img src="screenshots/light-xbox.png" alt=""> |
| **Interfaccia tradotta (日本語)** | **Area di notifica** |
| <img src="screenshots/japanese.png" alt=""> | <img src="screenshots/tray.png" width="260" alt=""> |

## Gesti del touchpad (modalità PS4)

Tieni premuto il pulsante assegnato al touchpad (**Acquisizione** per impostazione predefinita) e:

| Comando | Azione sul touchpad |
|---|---|
| Stick destro / sinistro | Dito 1 / dito 2: muovili entrambi per i **gesti a due dita** (ad es. «MOVE CAR» in *inFAMOUS Second Son*) |
| Croce direzionale | Scorrimento rapido in quella direzione (con ZL o ZR, a due dita) |
| L3 / R3 | Dito a sinistra / destra **+ clic** (entrambi = due dita + clic) |
| Ruotare il controller | Trascina un dito con il giroscopio (opzionale) |
| Tocco breve del pulsante | Clic |

Mentre il pulsante del touchpad è premuto, gli stick e la croce non vengono inviati al gioco.

## FAQ

<details><summary><b>Funziona via Bluetooth?</b></summary>
Non ancora, solo USB.
</details>

<details><summary><b>Quale modalità uso, Xbox o PS4?</b></summary>
Xbox 360 funziona con quasi tutti i giochi per PC. Usa PS4 per giroscopio o touchpad (emulatori PS4 come shadPS4, giochi compatibili con DS4, Steam).
</details>

<details><summary><b>Un gioco vede due controller.</b></summary>
Nascondi il controller fisico con <a href="https://github.com/nefarius/HidHide">HidHide</a>, oppure attiva la <i>priorità su Steam</i> se il secondo arriva da Steam Input.
</details>

<details><summary><b>Servono i permessi di amministratore?</b></summary>
Funziona come utente normale. Solo l'installazione di ViGEmBus (Windows) o delle regole udev (Linux) li chiede, una volta.
</details>

<details><summary><b>Quali controller sono supportati?</b></summary>
Pro Controller di Switch 2 (testato). Controller GameCube NSO: sperimentale. Joy-Con 2: non ancora.
</details>

## Compilare dal codice sorgente

```sh
pip install -r requirements.txt pyinstaller
python -m PyInstaller switch2pad.spec      # Windows -> dist/Switch2Pad.exe
sh build_linux.sh                           # Linux   -> dist/Switch2Pad-<version>-linux-x86_64.tar.gz
```

## Contribuire

Issue, idee, traduzioni e pull request sono benvenuti: vedi [CONTRIBUTING.md](../CONTRIBUTING.md). Se Switch2Pad ti è utile, **una ⭐ aiuta altre persone a trovarlo.**

---

<sub>Switch2Pad è un progetto indipendente e non è affiliato né approvato da Nintendo, Sony, Microsoft o Valve. Nintendo Switch, DualShock, Xbox e Steam sono marchi dei rispettivi proprietari.</sub>
