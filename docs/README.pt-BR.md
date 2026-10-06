<div align="center">

<img src="../assets/icon.png" width="112" alt="Switch2Pad">

# Switch2Pad

**Use o seu Pro Controller do Nintendo Switch 2 no PC como um controle de Xbox 360 ou DualShock 4, com giroscópio, gestos de touchpad e vibração.**

[![Release](https://img.shields.io/github/v/release/TomGGB/Switch2Pad?label=download&color=e60012)](https://github.com/TomGGB/Switch2Pad/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/TomGGB/Switch2Pad/total?color=e60012)](https://github.com/TomGGB/Switch2Pad/releases)
![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078d4)
![Linux](https://img.shields.io/badge/Linux-x86__64-f7a41d)

[English](../README.md) · [Español](README.es.md) · **Português** · [Français](README.fr.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [日本語](README.ja.md) · [简体中文](README.zh-CN.md)

<img src="screenshots/main.png" width="820" alt="Switch2Pad">

</div>

## Por que o Switch2Pad?

O Windows e a maioria dos jogos não entendem o Pro Controller do Switch 2 via USB: ele nem envia dados até receber uma sequência especial de inicialização. O Switch2Pad conversa diretamente com o controle e o transforma em um **Xbox 360 ou DualShock 4 virtual**, compatível com qualquer jogo, emulador ou launcher.

- 🎮 **Modo Xbox 360 ou PS4**: troque quando quiser, até durante o jogo.
- 🌀 **Giroscópio e acelerômetro** (modo PS4): mira por movimento em jogos e emuladores compatíveis com o DS4.
- ✌️ **Gestos de touchpad, inclusive com dois dedos**: segure *Captura* e os analógicos viram dedos; o direcional faz deslizes rápidos e L3/R3 clicam no lado esquerdo/direito.
- 🎯 **Mira com giroscópio em qualquer jogo**: mova o mouse ou o analógico direito movendo o controle, até no modo Xbox.
- 🗂️ **Perfis por jogo** que trocam sozinhos conforme o jogo em primeiro plano.
- ⌨️ **Atalhos com o botão C**, **turbo** por botão, **intensidade da vibração** e **curvas de resposta** dos analógicos.
- 📳 **Vibração** enviada do jogo para o controle.
- 🧊 **Controle em 3D ao vivo** que segue o giroscópio do controle real e acende os botões pressionados.
- 🚫 **Prioridade sobre a Steam**: com um clique a Steam para de tomar e remapear o controle.
- 🔧 **Remapeamento de todos os botões**, A/B/X/Y por posição ou por letra, zona morta dos analógicos.
- 🪟 **Visual nativo do Windows 11** (Mica, claro/escuro, cor de destaque), bandeja do sistema e início com o Windows.
- 🌍 **7 idiomas** e 🐧 **Windows e Linux**.

## Download

| Plataforma | Arquivo | Observações |
|---|---|---|
| **Windows 10/11** | [`Switch2Pad.exe`](https://github.com/TomGGB/Switch2Pad/releases/latest) | Sem instalação. Se faltar o [ViGEmBus](https://github.com/nefarius/ViGEmBus/releases), o app oferece instalá-lo. |
| **Linux x86_64** | [`Switch2Pad-<version>-linux-x86_64.tar.gz`](https://github.com/TomGGB/Switch2Pad/releases/latest) | Extraia e execute `./install.sh` (adiciona o atalho no menu e as regras udev). |

## Início rápido

1. Conecte o Pro Controller do Switch 2 com um **cabo USB-C**.
2. Abra o Switch2Pad e escolha **Xbox 360** ou **PS4 · DualShock 4**.
3. Jogue. Ao fechar a janela ele continua na bandeja do sistema.

> **Usa a Steam?** Abra a aba *Steam* e clique em **Dar prioridade ao Switch2Pad** para a Steam parar de tomar o controle (a Steam reinicia sozinha e um backup da configuração é guardado).

## Capturas de tela

| Gestos de touchpad e segundo plano | Remapeamento de botões |
|---|---|
| <img src="screenshots/touchpad.png" alt=""> | <img src="screenshots/buttons.png" alt=""> |
| **Prioridade sobre a Steam** | **Tema claro · modo Xbox** |
| <img src="screenshots/steam.png" alt=""> | <img src="screenshots/light-xbox.png" alt=""> |
| 🎯 | 🗂️ |
| <img src="screenshots/motion.png" alt=""> | <img src="screenshots/profiles.png" alt=""> |
| **Interface traduzida (日本語)** | **Bandeja do sistema** |
| <img src="screenshots/japanese.png" alt=""> | <img src="screenshots/tray.png" width="260" alt=""> |

## Gestos do touchpad (modo PS4)

Segure o botão atribuído ao touchpad (**Captura** por padrão) e:

| Entrada | Ação no touchpad |
|---|---|
| Analógico direito / esquerdo | Dedo 1 / dedo 2: mova os dois para **gestos de dois dedos** (por exemplo "MOVE CAR" em *inFAMOUS Second Son*) |
| Direcional | Deslize rápido nessa direção (com ZL ou ZR, de dois dedos) |
| L3 / R3 | Dedo no lado esquerdo / direito **+ clique** (os dois = dois dedos + clique) |
| Girar o controle | Arrasta um dedo com o giroscópio (opcional) |
| Toque curto no botão | Clique |

Enquanto o botão do touchpad estiver pressionado, os analógicos e o direcional não são enviados ao jogo.

## Perguntas frequentes

<details><summary><b>Funciona por Bluetooth?</b></summary>
Ainda não, apenas USB.
</details>

<details><summary><b>Qual modo usar, Xbox ou PS4?</b></summary>
O Xbox 360 funciona em quase todos os jogos de PC. Use PS4 se quiser giroscópio ou touchpad (emuladores de PS4 como o shadPS4, jogos compatíveis com DS4, Steam).
</details>

<details><summary><b>Um jogo vê dois controles.</b></summary>
Oculte o controle físico com o <a href="https://github.com/nefarius/HidHide">HidHide</a>, ou ative a <i>prioridade sobre a Steam</i> se o segundo vier do Steam Input.
</details>

<details><summary><b>Precisa de permissão de administrador?</b></summary>
Roda como usuário normal. Só a instalação do ViGEmBus (Windows) ou das regras udev (Linux) pede permissão, uma vez.
</details>

<details><summary><b>Quais controles são compatíveis?</b></summary>
Pro Controller do Switch 2 (testado). Controle de GameCube do NSO: experimental. Joy-Con 2: ainda não.
</details>

## Compilar a partir do código

```sh
pip install -r requirements.txt pyinstaller
python -m PyInstaller switch2pad.spec      # Windows -> dist/Switch2Pad.exe
sh build_linux.sh                           # Linux   -> dist/Switch2Pad-<version>-linux-x86_64.tar.gz
```

## Contribuir

Issues, ideias, traduções e pull requests são bem-vindos: veja [CONTRIBUTING.md](../CONTRIBUTING.md). Se o Switch2Pad te ajudou, **uma ⭐ ajuda outras pessoas a encontrá-lo.**

Licença [MIT](../LICENSE) © Tomás González. O modelo 3D do controle foi feito pelo autor.

---

<sub>O Switch2Pad é um projeto independente e não é afiliado nem endossado pela Nintendo, Sony, Microsoft ou Valve. Nintendo Switch, DualShock, Xbox e Steam são marcas de seus respectivos donos.</sub>
