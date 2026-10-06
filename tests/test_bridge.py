from conftest import make_state

from switch2pad import config as C
from switch2pad import foreground
from switch2pad.bridge import Bridge


class FakeOut:
    kind = "xbox"


def make_bridge():
    events = []
    b = Bridge(on_status=lambda code, **p: events.append((code, p)))
    b.events = events
    return b


def test_hotkeys_switch_mode_and_are_hidden_from_game():
    b = make_bridge()
    game = b.game_state(FakeOut(), make_state(["C", "X"]), 1.0)
    assert not game.buttons["C"] and not game.buttons["X"]
    assert b.cfg["emulate"] == "ps4" and C.load_config()["emulate"] == "ps4"
    assert ("hotkey", {"action": "emulate", "value": "ps4"}) in b.events
    b.game_state(FakeOut(), make_state(["C", "X"]), 1.1)   # mantener no repite
    assert b.cfg["emulate"] == "ps4"


def test_hotkeys_can_be_disabled():
    cfg = C.load_config()
    cfg["hotkeys"] = False
    C.save_config(cfg)
    b = make_bridge()
    game = b.game_state(FakeOut(), make_state(["C", "X"]), 1.0)
    assert game.buttons["X"] and b.cfg["emulate"] == "xbox"


def test_rumble_hotkey_and_profile_cycle():
    cfg = C.load_config()
    cfg["profiles"] = {"Juego": {"exes": ["juego.exe"], "settings": {"emulate": "ps4"}}}
    C.save_config(cfg)
    b = make_bridge()
    b.game_state(FakeOut(), make_state(["C", "DOWN"]), 1.0)
    assert b.cfg["rumble_strength"] == 75
    b.game_state(FakeOut(), make_state(["C"]), 1.1)
    b.game_state(FakeOut(), make_state(["C", "R"]), 1.2)
    assert b.active_profile == "Juego" and b.cfg["emulate"] == "ps4"


def test_turbo_alternates():
    cfg = C.load_config()
    cfg["turbo"], cfg["turbo_rate"] = ["A"], 10
    C.save_config(cfg)
    b = make_bridge()
    seen = {b.game_state(FakeOut(), make_state(["A"]), t / 100).buttons["A"] for t in range(0, 30)}
    assert seen == {True, False}


def test_profile_follows_foreground(monkeypatch):
    cfg = C.load_config()
    cfg["profiles"] = {"Juego": {"exes": ["juego.exe"], "settings": {"emulate": "ps4"}}}
    C.save_config(cfg)
    b = make_bridge()
    monkeypatch.setattr(foreground, "foreground_exe", lambda: "juego.exe")
    b._check_foreground(10.0)
    assert b.active_profile == "Juego" and b.cfg["emulate"] == "ps4"
    monkeypatch.setattr(foreground, "foreground_exe", lambda: "Switch2Pad.exe")
    b._check_foreground(20.0)
    assert b.active_profile == "Juego"          # la propia app al frente no cambia el perfil
    monkeypatch.setattr(foreground, "foreground_exe", lambda: "notepad.exe")
    b._check_foreground(30.0)
    assert b.active_profile == "" and ("profile", {"name": ""}) in b.events


def test_rstick_gyro_aim_reaches_game_state():
    cfg = C.load_config()
    cfg.update(gyro_aim="rstick", gyro_activation="always")
    C.save_config(cfg)
    b = make_bridge()
    b.game_state(FakeOut(), make_state(gyro=(0, -110, 0)), 1.0)
    game = b.game_state(FakeOut(), make_state(gyro=(0, -110, 0)), 1.01)
    assert game.aim[0] > 0.4
