from unittest import mock

import pytest


@pytest.fixture(
    scope="function",
    params=[
        "String",
        "Integer",
        "Float",
        "Decimal",
        "Boolean",
    ],
)
def non_positional_node(request):
    import colander

    node_klass = getattr(colander, request.param)
    yield node_klass


@pytest.fixture(scope="function", params=["Tuple", "Sequence"])
def positional_node(request):
    import colander

    node_klass = getattr(colander, request.param)
    yield node_klass


@pytest.mark.parametrize(
    "msg, expected",
    [
        ((), []),
        ([], []),
        (None, []),
        ("MESSAGE", ["MESSAGE"]),
    ],
)
def test_invalid_messages(msg, expected):
    import colander

    node = object()
    invalid = colander.Invalid(node, msg)

    assert list(invalid.messages()) == expected


_MARKER = object()


@pytest.mark.parametrize("pos", [_MARKER, None, 23])
def test_invalid_add_w_non_positional_node(non_positional_node, pos):
    import colander

    node = colander.SchemaNode(
        non_positional_node(),
        colander.SchemaNode(
            name="child",
            typ=colander.String(),
        ),
    )
    invalid = colander.Invalid(node)
    child_exc = colander.Invalid(object(), "testing")

    if pos is _MARKER:
        invalid.add(child_exc)
    else:
        invalid.add(child_exc, pos=pos)

    assert not child_exc.positional

    if pos not in (_MARKER, None):
        assert child_exc.pos == pos

    assert invalid.children[-1] is child_exc


@pytest.mark.parametrize("pos", [_MARKER, None, 23])
def test_invalid_add_w_positional_node(positional_node, pos):
    import colander

    node = colander.SchemaNode(
        positional_node(),
        colander.SchemaNode(
            name="child",
            typ=colander.String(),
        ),
    )
    invalid = colander.Invalid(node)
    child_exc = colander.Invalid(object(), "testing")

    if pos is _MARKER:
        invalid.add(child_exc)
    else:
        invalid.add(child_exc, pos=pos)

    assert child_exc.positional

    if pos not in (_MARKER, None):
        assert child_exc.pos == pos

    assert invalid.children[-1] is child_exc


@pytest.mark.parametrize(
    "name, pos_or_raises",
    [
        ("zero", 0),
        ("one", 1),
        ("two", 2),
        ("nonesuch", KeyError),
    ],
)
def test_invalid___setitem__(name, pos_or_raises):
    import colander

    MSG = "testing"

    class Node(colander.Schema):
        zero = colander.SchemaNode(
            colander.String(),
        )
        one = colander.SchemaNode(
            colander.String(),
        )
        two = colander.SchemaNode(
            colander.String(),
        )

    node = Node()
    invalid = colander.Invalid(node)
    invalid.add = mock.Mock(spec_set=())

    if not isinstance(pos_or_raises, int):

        with pytest.raises(pos_or_raises):
            invalid[name] = MSG

        invalid.add.assert_not_called()

    else:
        invalid[name] = MSG

        assert len(invalid.add.call_args_list) == 1
        args, kwargs = invalid.add.call_args_list[0]
        assert len(args) == 2
        assert isinstance(args[0], colander.Invalid)
        assert args[0].node is node.children[pos_or_raises]
        assert args[1] == pos_or_raises
        assert kwargs == {}


def test_invalid_paths_empty():
    import colander

    node = object()
    invalid = colander.Invalid(node, "empty")

    paths = list(invalid.paths())

    assert paths == [(invalid,)]


def test_invalid_paths_one_child():
    import colander

    node = object()
    invalid = colander.Invalid(node, "empty")
    child_exc = colander.Invalid(object(), "testing")
    invalid.children.append(child_exc)

    paths = list(invalid.paths())

    assert paths == [
        (invalid, child_exc),
    ]


def test_invalid_paths_multiple_children():
    import colander

    node = object()
    invalid = colander.Invalid(node, "parent")

    child_one = colander.Invalid(object(), "child one")
    invalid.children.append(child_one)

    child_two = colander.Invalid(object(), "child two")
    invalid.children.append(child_two)

    paths = list(invalid.paths())

    assert paths == [
        (invalid, child_one),
        (invalid, child_two),
    ]


def test_invalid_paths_multiple_children_grandchild():
    import colander

    node = object()
    invalid = colander.Invalid(node, "grandparent")

    child_one = colander.Invalid(object(), "child one")
    invalid.children.append(child_one)

    grandchild_one = colander.Invalid(object(), "grandchild one")
    child_one.children.append(grandchild_one)

    child_two = colander.Invalid(object(), "child two")
    invalid.children.append(child_two)

    paths = list(invalid.paths())

    assert paths == [
        (invalid, child_one, grandchild_one),
        (invalid, child_two),
    ]


def test_invalid__keyname_w_non_positional():
    import colander

    node = mock.Mock(spec_set=["name"])
    node.name = "Name"
    invalid = colander.Invalid(node, "testing")

    assert invalid._keyname() == "Name"


def test_invalid__keyname_w_positional():
    import colander

    node = object()
    invalid = colander.Invalid(node, "testing")
    invalid.positional = True
    invalid.pos = 42

    assert invalid._keyname() == "42"


# def test_invalid_asdict_blah_blah_not_gonna_do_it()
# def test_invalid___str___not_gonna_do_it()


def test_unsupportedfields___init___default():
    import colander

    node = object()
    usf = colander.UnsupportedFields(node, ["abc", "def"])

    assert usf.node is node
    assert usf.msg is None
    assert usf.fields == ["abc", "def"]


def test_unsupportedfields___init___explicit():
    import colander

    node = object()
    usf = colander.UnsupportedFields(node, ["abc", "def"], "MESSAGE")

    assert usf.node is node
    assert usf.msg == "MESSAGE"
    assert usf.fields == ["abc", "def"]
