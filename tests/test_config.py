from conftest import make_state

from switch2pad import config as C


def test_defaults_roundtrip():
    cfg = C.load_config()
    assert cfg["emulate"] == "xbox" and cfg["mapping"]["ZL"] == "LT"
    cfg["emulate"] = "ps4"
    C.save_config(cfg)
    assert C.load_config()["emulate"] == "ps4"


def test_profile_overrides_and_lookup():
    cfg = C.load_config()
    cfg["profiles"] = {"inFAMOUS": {"exes": ["shadPS4.exe"],
                                    "settings": {"emulate": "ps4", "mapping": {"GL": "A"}, "language": "ja"}}}
    eff = C.effective_config(cfg, "inFAMOUS")
    assert eff["emulate"] == "ps4" and eff["mapping"]["GL"] == "A"
    assert eff["mapping"]["ZL"] == "LT"            # el resto del mapeo se hereda
    assert eff["language"] == cfg["language"]      # las claves globales no se pisan
    assert eff["active_profile"] == "inFAMOUS"
    assert C.profile_for_exe(cfg, "SHADPS4.EXE") == "inFAMOUS"
    assert C.profile_for_exe(cfg, "other.exe") == ""
    assert C.effective_config(cfg, "missing")["active_profile"] == ""


def test_curve_and_inversion():
    assert C.apply_curve(0.5, 0, "linear") == (0.5, 0)
    x, _ = C.apply_curve(0.5, 0, "smooth")
    assert abs(x - 0.25) < 1e-9
    x, _ = C.apply_curve(0.5, 0, "fast")
    assert x > 0.5
    cfg = dict(C.load_config(), deadzone=0.0, invert_ry=True)
    _, (_, _, _, ry), _ = C.resolve(make_state(ry=0.5), C.build_mapping(cfg), cfg)
    assert ry == -0.5


def test_aim_added_after_deadzone():
    cfg = dict(C.load_config(), deadzone=0.2)
    s = make_state()
    s.aim = (0.05, -0.05)     # menor que la zona muerta y aun asi llega
    _, (_, _, rx, ry), _ = C.resolve(s, C.build_mapping(cfg), cfg)
    assert (rx, ry) == (0.05, -0.05)
