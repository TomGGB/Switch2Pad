import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Las pruebas nunca leen ni escriben la configuracion real del usuario."""
    from switch2pad import config
    monkeypatch.setattr(config, "CONFIG_PATH", str(tmp_path / "config.json"))
    monkeypatch.setattr(config, "config_dir", lambda: str(tmp_path))
    from switch2pad import foreground
    monkeypatch.setattr(foreground, "foreground_exe", lambda: None)
    return tmp_path


def make_state(buttons=(), lx=0.0, ly=0.0, rx=0.0, ry=0.0, gyro=(0.0, 0.0, 0.0), motion=True):
    from switch2pad.protocol import PHYSICAL_BUTTONS, ControllerState
    s = ControllerState()
    s.buttons = {n: n in buttons for n in PHYSICAL_BUTTONS}
    s.lx, s.ly, s.rx, s.ry = lx, ly, rx, ry
    s.gyro, s.accel, s.has_motion = gyro, (0.0, 1.0, 0.0), motion
    return s
