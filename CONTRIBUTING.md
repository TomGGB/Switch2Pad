# Contributing to Switch2Pad

Thanks for helping! Every bug report, idea, translation and pull request makes Switch2Pad better.

## Reporting bugs

Open an [issue](https://github.com/TomGGB/Switch2Pad/issues/new/choose) with:

- Switch2Pad version (shown at the bottom right of the window) and your OS.
- Controller model and whether you use **Xbox** or **PS4** mode.
- The game or emulator, and what you expected vs. what happened.
- For connection problems, the output of `Switch2Pad --cli` (or `python -m switch2pad --cli`).

## Translations

UI strings live in [`switch2pad/i18n.py`](switch2pad/i18n.py) — copy the `"en"` block, translate the
values and add the language to `LANGUAGES`. README translations live in [`docs/`](docs/).

## Development

```sh
pip install -r requirements.txt
python -m switch2pad          # GUI
python -m switch2pad --cli    # console mode
```

- `switch2pad/protocol.py` — USB initialization and input reports of the Switch 2 controllers.
- `switch2pad/outputs/` — virtual controllers (ViGEmBus on Windows, uinput on Linux).
- `switch2pad/touch.py` — DualShock 4 touchpad gestures.
- `switch2pad/gui/` — Qt interface and 3D view.

Keep pull requests focused, follow the style of the surrounding code and test with a real controller
when you touch the protocol or the outputs.
