def test__required___reduce__():
    from colander import _required

    not_the_singleton = _required()

    assert not_the_singleton.__reduce__() == "required"


def test_required_pickling():
    import pickle

    from colander import required as the_singleton

    pickled = pickle.dumps(the_singleton)

    unpickled = pickle.loads(pickled)

    assert unpickled is the_singleton


def test__null___bool__():
    from colander import _null

    not_the_singleton = _null()

    assert not not_the_singleton


def test__null___reduce__():
    from colander import _null

    not_the_singleton = _null()

    assert not_the_singleton.__reduce__() == "null"


def test__drop___reduce__():
    from colander import _drop

    not_the_singleton = _drop()

    assert not_the_singleton.__reduce__() == "drop"
