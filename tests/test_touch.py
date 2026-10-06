from conftest import make_state

from switch2pad.touch import PAD_W, TouchpadGesture


def test_two_finger_swipe_with_sticks():
    g = TouchpadGesture()
    g.update(True, make_state(["CAPTURE"]), now=0.0)
    t = g.update(True, make_state(["CAPTURE"], lx=0, ly=1, rx=0, ry=1), now=0.05)
    assert len(t.fingers) == 2 and all(f[3] < 300 for f in t.fingers)
    assert t.capturing


def test_l3_r3_click_on_each_side():
    g = TouchpadGesture()
    g.update(True, make_state(["CAPTURE"]), use_gyro=False, now=0.0)
    t = g.update(True, make_state(["CAPTURE", "LSTICK"]), use_gyro=False, now=0.05)
    assert t.click and len(t.fingers) == 1 and t.fingers[0][2] < PAD_W / 2
    t = g.update(True, make_state(["CAPTURE", "LSTICK", "RSTICK"]), use_gyro=False, now=0.1)
    assert t.click and len(t.fingers) == 2


def test_short_tap_clicks():
    g = TouchpadGesture()
    g.update(True, make_state(["CAPTURE"]), now=0.0)
    assert g.update(False, make_state(), now=0.1).click


def test_dpad_swipe_moves_and_lifts():
    g = TouchpadGesture()
    g.update(True, make_state(["CAPTURE"]), now=0.0)
    first = g.update(True, make_state(["CAPTURE", "UP"]), now=0.01).fingers[0][3]
    later = g.update(True, make_state(["CAPTURE", "UP"]), now=0.15).fingers[0][3]
    assert later < first
    assert g.update(True, make_state(["CAPTURE", "UP"]), now=0.4).fingers == []
