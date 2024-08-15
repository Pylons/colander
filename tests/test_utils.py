import pytest


def test_interpolate_w_empty_msgs():
    from colander import interpolate

    msgs = ()

    result = list(interpolate(msgs))

    assert result == []


def test_interpolate_w_msg_strings():
    from colander import interpolate

    msgs = ("abc", "def")

    result = list(interpolate(msgs))

    assert result == ["abc", "def"]


def test_interpolate_w_msg_objects_w_interpolate():
    from colander import interpolate

    class UppercaseDammit:

        def __init__(self, value):
            self.value = value

        def interpolate(self):
            return self.value.upper()

    msgs = [UppercaseDammit(x) for x in ("abc", "def")]

    result = list(interpolate(msgs))

    assert result == ["ABC", "DEF"]


def test_interpolate_w_msg_objects_wo_interpolate():
    from colander import interpolate

    abc, def_ = object(), object()
    msgs = [abc, def_]

    result = list(interpolate(msgs))

    assert result == [abc, def_]


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, False),
        (object(), False),
        ("", False),
        ((), True),
        ([], True),
        ({}, True),
    ],
)
def test_is_nonstr_iter(value, expected):
    from colander import is_nonstr_iter

    result = is_nonstr_iter(value)

    assert result == expected
