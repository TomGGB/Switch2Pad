<div align="center">

<img src="../assets/icon.png" width="112" alt="Switch2Pad">

# Switch2Pad

**在 PC 上把 Nintendo Switch 2 Pro 手柄当作 Xbox 360 或 DualShock 4 手柄使用——支持陀螺仪、触控板手势和震动。**

[![Release](https://img.shields.io/github/v/release/TomGGB/Switch2Pad?label=download&color=e60012)](https://github.com/TomGGB/Switch2Pad/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/TomGGB/Switch2Pad/total?color=e60012)](https://github.com/TomGGB/Switch2Pad/releases)
![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078d4)
![Linux](https://img.shields.io/badge/Linux-x86__64-f7a41d)

[English](../README.md) · [Español](README.es.md) · [Português](README.pt-BR.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [日本語](README.ja.md) · **简体中文**

<img src="screenshots/main.png" width="820" alt="Switch2Pad">

</div>

## 为什么选择 Switch2Pad？

Windows 和大多数游戏无法识别通过 USB 连接的 Switch 2 Pro 手柄：在收到特殊的初始化序列之前，它甚至不会发送任何输入。Switch2Pad 直接与手柄通信，把它变成所有游戏、模拟器和启动器都支持的**虚拟 Xbox 360 或 DualShock 4**。

- 🎮 **Xbox 360 或 PS4 模式**：随时切换，游戏中也可以。
- 🌀 **陀螺仪和加速度计**（PS4 模式）：在支持 DS4 体感的游戏和模拟器中使用体感瞄准。
- ✌️ **触控板手势，支持双指**：按住*截图键*，摇杆就变成手指；十字键快速滑动，L3/R3 点击触控板左/右侧。
- 🎯 **任何游戏都能体感瞄准**：移动手柄即可控制鼠标或右摇杆，Xbox 模式也可用。
- 🗂️ **按游戏的配置文件**，根据前台游戏自动切换。
- ⌨️ **C 键快捷键**、按键**连发**、**震动强度**和摇杆**响应曲线**。
- 📳 游戏发出的**震动**会传到手柄。
- 🧊 **实时 3D 手柄**，跟随真实手柄的陀螺仪转动并点亮按下的按键。
- 🚫 **优先于 Steam**：一键阻止 Steam 接管和重新映射手柄。
- 🔧 **重新映射所有按键**，A/B/X/Y 按位置或按字母，摇杆死区。
- 🪟 **原生 Windows 11 外观**（Mica、浅色/深色、强调色），系统托盘，开机自启。
- 🌍 **7 种界面语言**，🐧 **支持 Windows 和 Linux**。

## 下载

| 平台 | 文件 | 说明 |
|---|---|---|
| **Windows 10/11** | [`Switch2Pad.exe`](https://github.com/TomGGB/Switch2Pad/releases/latest) | 无需安装。如果缺少 [ViGEmBus](https://github.com/nefarius/ViGEmBus/releases)，应用会提示安装。 |
| **Linux x86_64** | [`Switch2Pad-<version>-linux-x86_64.tar.gz`](https://github.com/TomGGB/Switch2Pad/releases/latest) | 解压后运行 `./install.sh`（添加菜单项和 udev 规则）。 |

## 快速开始

1. 用 **USB-C 数据线**连接 Switch 2 Pro 手柄。
2. 打开 Switch2Pad，选择 **Xbox 360** 或 **PS4 · DualShock 4**。
3. 开始游戏。关闭窗口后应用会继续在系统托盘中运行。

> **在用 Steam？** 打开 *Steam* 选项卡，点击 **Give Switch2Pad priority**（让 Switch2Pad 优先），Steam 就不会再接管手柄（Steam 会自动重启，并保存配置备份）。

## 截图

| 触控板手势和后台运行 | 按键映射 |
|---|---|
| <img src="screenshots/touchpad.png" alt=""> | <img src="screenshots/buttons.png" alt=""> |
| **优先于 Steam** | **浅色主题 · Xbox 模式** |
| <img src="screenshots/steam.png" alt=""> | <img src="screenshots/light-xbox.png" alt=""> |
| 🎯 | 🗂️ |
| <img src="screenshots/motion.png" alt=""> | <img src="screenshots/profiles.png" alt=""> |
| **多语言界面（日本語）** | **系统托盘** |
| <img src="screenshots/japanese.png" alt=""> | <img src="screenshots/tray.png" width="260" alt=""> |

## 触控板手势（PS4 模式）

按住分配给触控板的按键（默认是**截图键**），然后：

| 输入 | 触控板动作 |
|---|---|
| 右 / 左摇杆 | 手指 1 / 手指 2——同时移动两个摇杆即可做**双指手势**（例如 *inFAMOUS Second Son* 中的「MOVE CAR」） |
| 十字键 | 朝该方向快速滑动（按住 ZL 或 ZR 为双指滑动） |
| L3 / R3 | 在左 / 右侧按下手指并**点击**（同时按 = 双指 + 点击） |
| 转动手柄 | 用陀螺仪拖动一根手指（可选） |
| 短按该按键 | 点击 |

按住触控板按键时，摇杆和十字键不会发送给游戏。

## 常见问题

<details><summary><b>支持蓝牙吗？</b></summary>
暂不支持，目前仅支持 USB。
</details>

<details><summary><b>该用 Xbox 还是 PS4 模式？</b></summary>
Xbox 360 适用于几乎所有 PC 游戏。如果需要陀螺仪或触控板，请用 PS4 模式（shadPS4 等 PS4 模拟器、支持 DS4 的游戏、Steam）。
</details>

<details><summary><b>游戏识别到两个手柄。</b></summary>
用 <a href="https://github.com/nefarius/HidHide">HidHide</a> 隐藏实体手柄；如果第二个来自 Steam Input，请开启<i>优先于 Steam</i>。
</details>

<details><summary><b>需要管理员权限吗？</b></summary>
以普通用户运行。只有安装 ViGEmBus（Windows）或 udev 规则（Linux）时需要一次管理员权限。
</details>

<details><summary><b>支持哪些手柄？</b></summary>
Switch 2 Pro 手柄（已测试）。NSO GameCube 手柄：实验性。Joy-Con 2：暂不支持。
</details>

## 从源码构建

```sh
pip install -r requirements.txt pyinstaller
python -m PyInstaller switch2pad.spec      # Windows -> dist/Switch2Pad.exe
sh build_linux.sh                           # Linux   -> dist/Switch2Pad-<version>-linux-x86_64.tar.gz
```

## 参与贡献

欢迎提交 Issue、想法、翻译和 Pull Request，详见 [CONTRIBUTING.md](../CONTRIBUTING.md)。如果 Switch2Pad 对你有帮助，**点个 ⭐ 能让更多人找到它。**

许可证：[MIT](../LICENSE) © Tomás González。手柄 3D 模型由作者制作。

---

<sub>Switch2Pad 是独立项目，与任天堂、索尼、微软和 Valve 无关，也未获其认可。Nintendo Switch、DualShock、Xbox 和 Steam 是其各自所有者的商标。</sub>
