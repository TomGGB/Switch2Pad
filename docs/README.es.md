<div align="center">

<img src="../assets/icon.png" width="112" alt="Switch2Pad">

# Switch2Pad

**Usa tu mando Pro de Nintendo Switch 2 en el PC como un mando de Xbox 360 o DualShock 4, con giroscopio, gestos de touchpad y vibración.**

[![Release](https://img.shields.io/github/v/release/TomGGB/Switch2Pad?label=download&color=e60012)](https://github.com/TomGGB/Switch2Pad/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/TomGGB/Switch2Pad/total?color=e60012)](https://github.com/TomGGB/Switch2Pad/releases)
![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078d4)
![Linux](https://img.shields.io/badge/Linux-x86__64-f7a41d)

[English](../README.md) · **Español** · [Português](README.pt-BR.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [日本語](README.ja.md) · [简体中文](README.zh-CN.md)

<img src="screenshots/main.png" width="820" alt="Switch2Pad">

</div>

## ¿Por qué Switch2Pad?

Windows y la mayoría de los juegos no entienden el mando Pro de Switch 2 por USB: ni siquiera envía datos hasta recibir una secuencia de inicialización especial. Switch2Pad se comunica directamente con el mando y lo convierte en un **Xbox 360 o DualShock 4 virtual**, compatible con cualquier juego, emulador o launcher.

- 🎮 **Modo Xbox 360 o PS4**: cámbialo cuando quieras, incluso jugando.
- 🌀 **Giroscopio y acelerómetro** (modo PS4): apuntado por movimiento en juegos y emuladores compatibles con el DS4.
- ✌️ **Gestos de touchpad, también con dos dedos**: mantén *Captura* y los sticks pasan a ser dedos; la cruceta hace deslizamientos rápidos y L3/R3 pulsan el lado izquierdo/derecho.
- 🎯 **Apuntar con el giroscopio en cualquier juego**: mueve el ratón o el stick derecho moviendo el mando, también en modo Xbox.
- 🗂️ **Perfiles por juego** que cambian solos con el juego en primer plano.
- ⌨️ **Atajos con el botón C**, **turbo** por botón, **intensidad de vibración** y **curvas de respuesta** de los sticks.
- 📳 **Vibración** que el juego envía al mando.
- 🧊 **Mando en 3D en vivo** que sigue el giroscopio del mando real e ilumina los botones pulsados.
- 🚫 **Prioridad sobre Steam**: con un clic Steam deja de tomar y remapear el mando.
- 🔧 **Remapeo de todos los botones**, A/B/X/Y por posición o por letra, zona muerta de los sticks.
- 🪟 **Aspecto nativo de Windows 11** (Mica, claro/oscuro, color de acento), bandeja del sistema e inicio con Windows.
- 🌍 **7 idiomas** y 🐧 **Windows y Linux**.

## Descarga

| Plataforma | Archivo | Notas |
|---|---|---|
| **Windows 10/11** | [`Switch2Pad.exe`](https://github.com/TomGGB/Switch2Pad/releases/latest) | Sin instalación. Si falta [ViGEmBus](https://github.com/nefarius/ViGEmBus/releases), la app ofrece instalarlo. |
| **Linux x86_64** | [`Switch2Pad-<version>-linux-x86_64.tar.gz`](https://github.com/TomGGB/Switch2Pad/releases/latest) | Extrae y ejecuta `./install.sh` (añade el acceso al menú y las reglas udev). |

## Inicio rápido

1. Conecta el mando Pro de Switch 2 con un **cable USB-C**.
2. Abre Switch2Pad y elige **Xbox 360** o **PS4 · DualShock 4**.
3. A jugar. Al cerrar la ventana sigue funcionando en la bandeja del sistema.

> **¿Usas Steam?** Abre la pestaña *Steam* y pulsa **Dar prioridad a Switch2Pad** para que Steam deje de quedarse con el mando (Steam se reinicia solo y se guarda una copia de su configuración).

## Capturas

| Gestos de touchpad y segundo plano | Remapeo de botones |
|---|---|
| <img src="screenshots/touchpad.png" alt=""> | <img src="screenshots/buttons.png" alt=""> |
| **Prioridad sobre Steam** | **Tema claro · modo Xbox** |
| <img src="screenshots/steam.png" alt=""> | <img src="screenshots/light-xbox.png" alt=""> |
| 🎯 | 🗂️ |
| <img src="screenshots/motion.png" alt=""> | <img src="screenshots/profiles.png" alt=""> |
| **Interfaz traducida (日本語)** | **Bandeja del sistema** |
| <img src="screenshots/japanese.png" alt=""> | <img src="screenshots/tray.png" width="260" alt=""> |

## Gestos del touchpad (modo PS4)

Mantén pulsado el botón asignado al touchpad (**Captura** por defecto) y:

| Entrada | Acción en el touchpad |
|---|---|
| Stick derecho / izquierdo | Dedo 1 / dedo 2: mueve los dos para **gestos de dos dedos** (por ejemplo «MOVE CAR» en *inFAMOUS Second Son*) |
| Cruceta | Deslizamiento rápido en esa dirección (con ZL o ZR, de dos dedos) |
| L3 / R3 | Dedo en el lado izquierdo / derecho **+ clic** (los dos = dos dedos + clic) |
| Girar el mando | Arrastra un dedo con el giroscopio (opcional) |
| Toque corto del botón | Clic |

Mientras mantienes el botón del touchpad, los sticks y la cruceta no se envían al juego.

## Preguntas frecuentes

<details><summary><b>¿Funciona por Bluetooth?</b></summary>
Todavía no, solo por USB.
</details>

<details><summary><b>¿Qué modo uso, Xbox o PS4?</b></summary>
Xbox 360 funciona en casi todos los juegos de PC. Usa PS4 si quieres giroscopio o touchpad (emuladores de PS4 como shadPS4, juegos compatibles con DS4, Steam).
</details>

<details><summary><b>Un juego ve dos mandos.</b></summary>
Oculta el mando físico con <a href="https://github.com/nefarius/HidHide">HidHide</a>, o activa la <i>prioridad sobre Steam</i> si el segundo viene de Steam Input.
</details>

<details><summary><b>¿Necesita permisos de administrador?</b></summary>
Funciona como usuario normal. Solo la instalación de ViGEmBus (Windows) o de las reglas udev (Linux) pide permisos, una vez.
</details>

<details><summary><b>¿Qué mandos son compatibles?</b></summary>
Mando Pro de Switch 2 (probado). Mando de GameCube de NSO: experimental. Joy-Con 2: todavía no.
</details>

## Compilar desde el código

```sh
pip install -r requirements.txt pyinstaller
python -m PyInstaller switch2pad.spec      # Windows -> dist/Switch2Pad.exe
sh build_linux.sh                           # Linux   -> dist/Switch2Pad-<version>-linux-x86_64.tar.gz
```

## Contribuir

Los issues, ideas, traducciones y pull requests son bienvenidos: consulta [CONTRIBUTING.md](../CONTRIBUTING.md). Si Switch2Pad te sirve, **una ⭐ ayuda a que otras personas lo encuentren.**

Licencia [MIT](../LICENSE) © Tomás González. El modelo 3D del mando es obra del autor.

---

<sub>Switch2Pad es un proyecto independiente y no está afiliado ni respaldado por Nintendo, Sony, Microsoft ni Valve. Nintendo Switch, DualShock, Xbox y Steam son marcas de sus respectivos propietarios.</sub>
