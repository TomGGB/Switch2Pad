from conftest import make_state

from switch2pad.gyroaim import GyroAim


def cfg(**kw):
    base = {"gyro_aim": "mouse", "gyro_activation": "always", "gyro_button": "ZL", "gyro_sens": 1.0,
            "gyro_axis": "yaw", "gyro_invert_y": False}
    base.update(kw)
    return base


def run(aim, c, state, frames=50, dt=0.01):
    total = [0, 0]
    t = 100.0
    out = None
    for _ in range(frames):
        out = aim.update(state, c, now=t)
        if out and out[0] == "mouse":
            total[0] += out[1]
            total[1] += out[2]
        t += dt
    return total, out


def test_turn_right_moves_right_and_tip_up_moves_up():
    total, _ = run(GyroAim(), cfg(), make_state(gyro=(0, -100, 0)))   # girar a la derecha
    assert total[0] > 50 and total[1] == 0
    total, _ = run(GyroAim(), cfg(), make_state(gyro=(100, 0, 0)))    # levantar la punta
    assert total[1] < -50


def test_hold_and_toggle_activation():
    aim = GyroAim()
    total, _ = run(aim, cfg(gyro_activation="hold"), make_state(gyro=(0, -100, 0)))
    assert total == [0, 0]
    total, _ = run(aim, cfg(gyro_activation="hold"), make_state(["ZL"], gyro=(0, -100, 0)))
    assert total[0] > 0
    aim = GyroAim()
    c = cfg(gyro_activation="toggle")
    assert aim.update(make_state(["ZL"], gyro=(0, -100, 0)), c, now=1.0)        # pulsar: activa
    assert aim.update(make_state([], gyro=(0, -100, 0)), c, now=1.01)            # sigue activo
    aim.update(make_state(["ZL"], gyro=(0, -100, 0)), c, now=1.02)               # pulsar otra vez
    assert aim.update(make_state([], gyro=(0, -100, 0)), c, now=1.03) is None    # desactivado


def test_deadband_and_rstick_mode():
    total, _ = run(GyroAim(), cfg(), make_state(gyro=(0.5, -0.8, 0)))
    assert total == [0, 0]
    _, out = run(GyroAim(), cfg(gyro_aim="rstick"), make_state(gyro=(0, -110, 0)), frames=2)
    assert out[0] == "rstick" and 0.45 < out[1] < 0.55


def test_off_and_suspended():
    assert GyroAim().update(make_state(gyro=(0, -100, 0)), cfg(gyro_aim="off")) is None
    aim = GyroAim()
    aim.suspended = True
    assert aim.update(make_state(gyro=(0, -100, 0)), cfg()) is None
