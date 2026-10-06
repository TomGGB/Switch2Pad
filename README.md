# Switch2Pad

Usa el mando de **Nintendo Switch 2** conectado por **USB** como un mando de **Xbox 360** o de
**PS4 (DualShock 4)** en **Windows** y **Linux**. En modo PS4 también se envían el giroscopio y el
acelerómetro (sensor de movimiento).

- **Mando en 3D en vivo**: modelo del Switch 2 Pro Controller (silueta trazada de una foto real) que
  gira con el giroscopio del mando, ilumina los botones pulsados y se puede girar con el ratón.
- Remapeo de todos los botones, vibración, zona muerta y distribución A/B/X/Y por posición o por letra.
- **Touchpad del DualShock 4 con gestos de uno y dos dedos** (modo PS4). Mantén el botón del touchpad
  (Captura por defecto) y:
  - Stick derecho / izquierdo = dedo 1 / dedo 2. Mueve los dos a la vez para gestos de dos dedos
    (por ejemplo "MOVE CAR" en inFAMOUS Second Son: Captura + los dos sticks hacia arriba).
  - Cruceta = deslizamiento rápido; con ZL o ZR, de dos dedos.
  - L3 / R3 = clic del touchpad con los dedos apoyados. Girar el mando = arrastrar un dedo (opcional).
  - Toque corto del botón = clic.
  Mientras se mantiene el botón, los sticks y la cruceta no llegan al juego.
- **Segundo plano**: al cerrar con la X la app sigue en la bandeja del sistema, con acciones rápidas
  (cambiar Xbox/PS4, vibración, movimiento, touchpad, prioridad sobre Steam, salir). Puede iniciarse
  con el sistema.
- **Prioridad sobre Steam**: Steam deja de tomar el mando para que valga el mapeo de Switch2Pad.
- Idiomas: español, English, português, français, Deutsch, italiano, 日本語.
- Windows 11: estilo nativo con fondo **Mica**, modo claro/oscuro y color de acento del sistema.

## Windows

1. Ejecuta `Switch2Pad.exe` (no necesita instalación).
2. Si falta el driver **ViGEmBus**, la app muestra el botón **Instalar ViGEmBus** (trae el instalador).
3. Conecta el mando por USB-C y elige el mando a simular (Xbox 360 o PS4).

## Linux

```sh
tar -xzf Switch2Pad-2.2.0-linux-x86_64.tar.gz
cd Switch2Pad-2.2.0-linux-x86_64
./install.sh          # instala en ~/.local y, con sudo, las reglas udev
```

`install.sh` copia la app a `~/.local/opt/switch2pad`, crea el acceso en el menú y ejecuta
`install-udev-rules.sh`, que da acceso al mando USB y a `/dev/uinput` sin root y carga `uinput` al
arrancar. Vuelve a conectar el mando después de instalar las reglas.

En Linux la app suelta el driver del kernel y lee el mando directamente por USB: mientras está
abierta, ni el sistema ni Steam ven el mando original, solo el virtual. Los mandos virtuales imitan a
los de los drivers del kernel (xpad y hid-playstation, con su dispositivo "Motion Sensors"), así que SDL,
Steam y Proton los reconocen igual que a los de verdad.

## Prioridad sobre Steam

Steam abre el mando de Switch 2 por su cuenta y lo remapea con Steam Input. En la pestaña **Steam**,
**Dar prioridad a Switch2Pad** añade el mando a la lista `controller_blacklist` de
`<Steam>/config/config.vdf`. Steam se cierra y se vuelve a abrir solo, porque sobrescribe ese
archivo al cerrarse. Se guarda una copia en `config.vdf.switch2pad-backup`. **Devolver el mando a
Steam** deshace el cambio.

La opción **Ocultar también el mando virtual a Steam** evita que Steam Input remapee el mando Xbox/PS4
virtual. Afecta también a mandos Xbox 360 / DualShock 4 reales conectados al mismo PC.

Si al abrir la app Steam ya tiene el mando, la barra de estado lo indica y ofrece el mismo botón.

## Xbox o PS4

| | Xbox 360 | PS4 (DualShock 4) |
|---|---|---|
| Compatibilidad | Casi todos los juegos de PC | Juegos con soporte de mando PS4, emuladores, Steam |
| Giroscopio / movimiento | No (XInput no lo admite) | Sí |
| Touchpad | — | Gestos de uno y dos dedos, deslizamientos y clic (botón Captura) |

## Configuración

Se guarda en `%APPDATA%\Switch2Pad\config.json` (Windows) o `~/.config/switch2pad/config.json` (Linux).
Modo sin interfaz: `Switch2Pad --cli [--emulate xbox|ps4]`. Arrancar en la bandeja: `Switch2Pad --minimized`.

## Compilar

- Windows: `build_windows.bat` → `dist\Switch2Pad.exe`
- Linux: `sh build_linux.sh` → `dist/Switch2Pad-<versión>-linux-x86_64.tar.gz`. Para máxima compatibilidad
  compila en una distro con glibc antigua (Ubuntu 22.04).
- GitHub Actions: `.github/workflows/build.yml` compila ambas al publicar una etiqueta `v*`.

## Mandos compatibles

- Switch 2 Pro Controller (probado).
- Mando GameCube de Nintendo Switch Online (057E:2073): experimental.
- Joy-Con 2: todavía no.

Protocolo basado en el driver Switch 2 de SDL (`SDL_hidapi_switch2.c`).
