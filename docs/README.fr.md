<div align="center">

<img src="../assets/icon.png" width="112" alt="Switch2Pad">

# Switch2Pad

**Utilisez votre manette Pro Nintendo Switch 2 sur PC comme une manette Xbox 360 ou DualShock 4, avec gyroscope, gestes du pavé tactile et vibrations.**

[![Release](https://img.shields.io/github/v/release/TomGGB/Switch2Pad?label=download&color=e60012)](https://github.com/TomGGB/Switch2Pad/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/TomGGB/Switch2Pad/total?color=e60012)](https://github.com/TomGGB/Switch2Pad/releases)
![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078d4)
![Linux](https://img.shields.io/badge/Linux-x86__64-f7a41d)

[English](../README.md) · [Español](README.es.md) · [Português](README.pt-BR.md) · **Français** · [Deutsch](README.de.md) · [Italiano](README.it.md) · [日本語](README.ja.md) · [简体中文](README.zh-CN.md)

<img src="screenshots/main.png" width="820" alt="Switch2Pad">

</div>

## Pourquoi Switch2Pad ?

Windows et la plupart des jeux ne comprennent pas la manette Pro Switch 2 en USB : elle n'envoie même rien avant de recevoir une séquence d'initialisation spéciale. Switch2Pad communique directement avec la manette et la transforme en **Xbox 360 ou DualShock 4 virtuelle**, reconnue par tous les jeux, émulateurs et launchers.

- 🎮 **Mode Xbox 360 ou PS4** : changez quand vous voulez, même en jeu.
- 🌀 **Gyroscope et accéléromètre** (mode PS4) : visée par mouvement dans les jeux et émulateurs compatibles DS4.
- ✌️ **Gestes du pavé tactile, même à deux doigts** : maintenez *Capture* et les sticks deviennent des doigts ; la croix fait des glissements rapides et L3/R3 cliquent à gauche/droite.
- 📳 **Vibrations** transmises du jeu à la manette.
- 🧊 **Manette 3D en direct** qui suit le gyroscope de la vraie manette et éclaire les boutons pressés.
- 🚫 **Priorité sur Steam** : en un clic, Steam arrête de prendre et de reconfigurer la manette.
- 🔧 **Réassignation de tous les boutons**, A/B/X/Y par position ou par lettre, zone morte des sticks.
- 🪟 **Look natif Windows 11** (Mica, clair/sombre, couleur d'accent), zone de notification et démarrage avec Windows.
- 🌍 **7 langues** et 🐧 **Windows et Linux**.

## Téléchargement

| Plateforme | Fichier | Remarques |
|---|---|---|
| **Windows 10/11** | [`Switch2Pad.exe`](https://github.com/TomGGB/Switch2Pad/releases/latest) | Aucune installation. Si [ViGEmBus](https://github.com/nefarius/ViGEmBus/releases) manque, l'application propose de l'installer. |
| **Linux x86_64** | [`Switch2Pad-<version>-linux-x86_64.tar.gz`](https://github.com/TomGGB/Switch2Pad/releases/latest) | Extrayez et lancez `./install.sh` (ajoute l'entrée de menu et les règles udev). |

## Démarrage rapide

1. Branchez la manette Pro Switch 2 avec un **câble USB-C**.
2. Ouvrez Switch2Pad et choisissez **Xbox 360** ou **PS4 · DualShock 4**.
3. Jouez. En fermant la fenêtre, l'application reste dans la zone de notification.

> **Vous utilisez Steam ?** Ouvrez l'onglet *Steam* et cliquez sur **Donner la priorité à Switch2Pad** pour que Steam ne s'empare plus de la manette (Steam redémarre seul ; une sauvegarde de sa configuration est conservée).

## Captures d'écran

| Gestes du pavé tactile et arrière-plan | Réassignation des boutons |
|---|---|
| <img src="screenshots/touchpad.png" alt=""> | <img src="screenshots/buttons.png" alt=""> |
| **Priorité sur Steam** | **Thème clair · mode Xbox** |
| <img src="screenshots/steam.png" alt=""> | <img src="screenshots/light-xbox.png" alt=""> |
| **Interface traduite (日本語)** | **Zone de notification** |
| <img src="screenshots/japanese.png" alt=""> | <img src="screenshots/tray.png" width="260" alt=""> |

## Gestes du pavé tactile (mode PS4)

Maintenez le bouton attribué au pavé tactile (**Capture** par défaut) et :

| Commande | Action sur le pavé tactile |
|---|---|
| Stick droit / gauche | Doigt 1 / doigt 2 : bougez les deux pour les **gestes à deux doigts** (par ex. « MOVE CAR » dans *inFAMOUS Second Son*) |
| Croix | Glissement rapide dans cette direction (avec ZL ou ZR, à deux doigts) |
| L3 / R3 | Doigt à gauche / à droite **+ clic** (les deux = deux doigts + clic) |
| Tourner la manette | Fait glisser un doigt avec le gyroscope (optionnel) |
| Appui bref sur le bouton | Clic |

Tant que le bouton du pavé tactile est maintenu, les sticks et la croix ne sont pas envoyés au jeu.

## FAQ

<details><summary><b>Ça marche en Bluetooth ?</b></summary>
Pas encore, uniquement en USB.
</details>

<details><summary><b>Quel mode choisir, Xbox ou PS4 ?</b></summary>
Xbox 360 fonctionne avec presque tous les jeux PC. Choisissez PS4 pour le gyroscope ou le pavé tactile (émulateurs PS4 comme shadPS4, jeux compatibles DS4, Steam).
</details>

<details><summary><b>Un jeu voit deux manettes.</b></summary>
Masquez la manette physique avec <a href="https://github.com/nefarius/HidHide">HidHide</a>, ou activez la <i>priorité sur Steam</i> si la seconde vient de Steam Input.
</details>

<details><summary><b>Faut-il des droits administrateur ?</b></summary>
L'application tourne en utilisateur normal. Seule l'installation de ViGEmBus (Windows) ou des règles udev (Linux) les demande, une fois.
</details>

<details><summary><b>Quelles manettes sont compatibles ?</b></summary>
Manette Pro Switch 2 (testée). Manette GameCube NSO : expérimentale. Joy-Con 2 : pas encore.
</details>

## Compiler depuis les sources

```sh
pip install -r requirements.txt pyinstaller
python -m PyInstaller switch2pad.spec      # Windows -> dist/Switch2Pad.exe
sh build_linux.sh                           # Linux   -> dist/Switch2Pad-<version>-linux-x86_64.tar.gz
```

## Contribuer

Issues, idées, traductions et pull requests sont les bienvenus : voir [CONTRIBUTING.md](../CONTRIBUTING.md). Si Switch2Pad vous aide, **une ⭐ aide d'autres personnes à le trouver.**

---

<sub>Switch2Pad est un projet indépendant, ni affilié ni approuvé par Nintendo, Sony, Microsoft ou Valve. Nintendo Switch, DualShock, Xbox et Steam sont des marques de leurs propriétaires respectifs.</sub>
