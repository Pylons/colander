from unittest import mock

import pytest
import translationstring

NODE_NAME = "test_node"
NODE_VALUE = "test_node_value"
MARKER = object()
UNI = str(b'\xe3\x81\x82', 'utf-8')
UTF8 = UNI.encode("utf-8")
UTF16 = UNI.encode("utf-16")


@pytest.mark.parametrize(
    "prefix, listitem, exp_key",
    [
        (None, None, NODE_NAME),
        (None, False, NODE_NAME),
        (None, True, ""),
        ("foo", None, f"foo{NODE_NAME}"),
        ("foo", False, f"foo{NODE_NAME}"),
        ("foo", True, "foo"),
        ("foo.", None, f"foo.{NODE_NAME}"),
        ("foo.", False, f"foo.{NODE_NAME}"),
        ("foo.", True, "foo"),
    ],
)
def test_SchemaType_flatten(prefix, listitem, exp_key):
    from colander import SchemaType

    node = mock.Mock(spec_set=["name"])
    node.name = NODE_NAME
    appstruct = mock.Mock(spec_set=())
    typ = SchemaType()

    kw = {}

    if prefix is not None:
        kw["prefix"] = prefix

    if listitem is not None:
        kw["listitem"] = listitem

    result = typ.flatten(node, appstruct, **kw)

    assert result == {exp_key: appstruct}


def test_SchemaType_unflatten():
    from colander import SchemaType

    node = mock.Mock(spec_set=["name"])
    node.name = NODE_NAME
    paths = [NODE_NAME]
    appstruct = mock.Mock(spec_set=())
    fstruct = {NODE_NAME: appstruct}
    typ = SchemaType()

    assert typ.unflatten(node, paths, fstruct) is appstruct


def test_SchemaType_set_value():
    from colander import SchemaType

    node = mock.Mock(spec_set=["name"])
    node.name = NODE_NAME
    appstruct = mock.Mock(spec_set=())
    path = NODE_NAME
    typ = SchemaType()

    with pytest.raises(AssertionError):
        typ.set_value(node, appstruct, path, NODE_VALUE)


def test_SchemaType_get_value():
    from colander import SchemaType

    node = mock.Mock(spec_set=["name"])
    node.name = NODE_NAME
    appstruct = mock.Mock(spec_set=())
    path = NODE_NAME
    typ = SchemaType()

    with pytest.raises(AssertionError):
        typ.get_value(node, appstruct, path)


def test_SchemaType_cstruct_children():
    from colander import SchemaType

    node = mock.Mock(spec_set=())
    cstruct = mock.Mock(spec_set=())
    typ = SchemaType()

    assert typ.cstruct_children(node, cstruct) == []


@pytest.mark.parametrize(
    "unknown, exp_unknown",
    [
        (None, "ignore"),
        ("ignore", "ignore"),
        ("raise", "raise"),
        ("preserve", "preserve"),
    ],
)
def test_Mapping_ctor(unknown, exp_unknown):
    from colander import Mapping

    kw = {}
    if unknown is not None:
        kw["unknown"] = unknown

    typ = Mapping(**kw)

    assert typ.unknown == exp_unknown


@pytest.mark.parametrize(
    "value, raises",
    [
        ("ignore", False),
        ("raise", False),
        ("preserve", False),
        ("bogus", True),
    ],
)
def test_Mapping_unknwon_setter(value, raises):
    from colander import Mapping

    typ = Mapping()

    if raises:
        with pytest.raises(ValueError):
            typ.unknown = value
    else:
        typ.unknown = value
        assert typ.unknown == value


@pytest.mark.parametrize("value", [None, "", [], ()])
def test_Mapping__validate_miss(value):
    from colander import Invalid
    from colander import Mapping

    node = mock.Mock(spec_set=())
    typ = Mapping()

    with pytest.raises(Invalid) as exc:
        typ._validate(node, value)

    invalid = exc.value
    assert invalid.node is node
    assert isinstance(invalid.msg, translationstring.TranslationString)
    assert invalid.msg.default == '"${val}" is not a mapping type: ${err}'
    assert invalid.msg.mapping["val"] is value

    err = invalid.msg.mapping["err"]
    assert isinstance(err, TypeError)
    assert err.args == ("Does not implement dict-like functionality.",)


def test_Mapping__validate_w_dict():
    from colander import Mapping

    node = mock.Mock(spec_set=())
    value = {"foo": "Foo"}
    typ = Mapping()

    result = typ._validate(node, value)

    assert result == value


def test_Mapping__validate_w_dictlike():
    from collections import abc

    from colander import Mapping

    node = mock.Mock(spec_set=())
    value = mock.create_autospec(abc.Mapping)
    value.items = [("foo", "Foo")]
    expected = dict(value)
    typ = Mapping()

    result = typ._validate(node, value)

    assert result == expected


def test_Mapping_cstruct_children_w_null_wo_children():
    from colander import Mapping
    from colander import null

    node = mock.Mock(spec_set=["children"])
    node.children = []
    typ = Mapping()

    result = typ.cstruct_children(node, null)

    assert result == []


def test_Mapping_cstruct_children_w_null_w_children():
    from colander import Mapping
    from colander import null

    node = mock.Mock(spec_set=["children"])
    subnode = mock.Mock(spec_set=["name", "serialize"])
    subnode.name = "sub"
    node.children = [subnode]
    typ = Mapping()

    result = typ.cstruct_children(node, null)

    assert result == [subnode.serialize.return_value]


def test_Mapping_cstruct_children_w_dict_wo_children():
    from colander import Mapping

    node = mock.Mock(spec_set=["children"])
    node.children = []
    typ = Mapping()

    result = typ.cstruct_children(node, {"foo": "Foo"})

    assert result == []


def test_Mapping_cstruct_children_w_dict_w_children():
    from colander import Mapping

    node = mock.Mock(spec_set=["children"])
    node.children = []
    subnode_1 = mock.Mock(spec_set=["name", "serialize"])
    subnode_1.name = "foo"
    subnode_2 = mock.Mock(spec_set=["name", "serialize"])
    subnode_2.name = "bar"
    node.children = [subnode_1, subnode_2]
    typ = Mapping()

    result = typ.cstruct_children(node, {"foo": "Foo"})

    assert result == ["Foo", subnode_2.serialize.return_value]


@pytest.mark.parametrize(
    "unknown, cstruct, exp_or_raises",
    [
        ("ignore", "null", "null"),
        ("ignore", {}, {}),
        ("ignore", {"foo": "Foo"}, {}),
        ("preserve", {"foo": "Foo"}, {"foo": "Foo"}),
        ("raise", {"foo": "Foo"}, "UnsupportedFields"),
    ],
)
def test_Mapping_deserialize_wo_children(unknown, cstruct, exp_or_raises):
    from colander import Mapping
    from colander import UnsupportedFields
    from colander import null

    if cstruct == "null":
        cstruct = null

    if exp_or_raises == "null":
        exp_or_raises = null

    node = mock.Mock(spec_set=["children"])
    node.children = []
    typ = Mapping(unknown)

    if exp_or_raises == "UnsupportedFields":
        with pytest.raises(UnsupportedFields):
            typ.deserialize(node, cstruct)
    else:
        result = typ.deserialize(node, cstruct)

        assert result == exp_or_raises


def test_Mapping_deserialize_w_child_wo_missing():
    from colander import Invalid
    from colander import Mapping
    from colander import null

    node = mock.Mock(spec_set=["children", "typ"])
    sub = mock.Mock(spec_set=["name", "deserialize", "missing"])

    sub.name = "foo"
    sub.missing = None

    def _assert_not_null(value):
        if value is null:
            raise Invalid(sub)

    sub.deserialize = _assert_not_null

    node.children = [sub]
    typ = Mapping()
    cstruct = {}

    with pytest.raises(Invalid):
        typ.deserialize(node, cstruct)


@pytest.mark.parametrize(
    "cstruct, exp_appstruct",
    [
        ("null", "null"),
        ({}, {"foo": "Foo", "baz": "null"}),
        ({"foo": "Foo"}, {"foo": "Foo", "baz": "null"}),
        (
            {"foo": "Foo", "bar": "Bar"},
            {"foo": "Foo", "bar": "Bar", "baz": "null"},
        ),
        (
            {"foo": "drop", "bar": "Bar"},
            {"bar": "Bar", "baz": "null"},
        ),
        (
            {"foo": "subdrop", "bar": "Bar"},
            {"bar": "Bar", "baz": "null"},
        ),
        (
            {"foo": "Foo", "baz": "Baz"},
            {"foo": "Foo", "baz": "Baz"},
        ),
        (
            {"foo": "Foo", "bar": "Bar", "baz": "Baz"},
            {"foo": "Foo", "bar": "Bar", "baz": "Baz"},
        ),
    ],
)
def test_Mapping_deserialize_w_children(cstruct, exp_appstruct):
    from colander import Mapping
    from colander import drop
    from colander import null

    if cstruct == "null":
        cstruct = null
    else:
        for key, value in list(cstruct.items()):
            if value == "drop":
                cstruct[key] = drop

    if exp_appstruct == "null":
        exp_appstruct = null
    else:
        for key, value in list(exp_appstruct.items()):
            if value == "null":
                exp_appstruct[key] = null

    def _make_subnode(name, missing):
        sub = mock.Mock(spec_set=["name", "deserialize", "missing"])
        sub.name = name
        if cstruct is not null and cstruct.get(name) == "subdrop":
            sub.deserialize.return_value = drop
        elif exp_appstruct is not null and name in exp_appstruct:
            sub.deserialize.return_value = exp_appstruct[name]
        else:
            sub.deserialize.side_effect = AssertionError
        sub.missing = missing
        return sub

    node = mock.Mock(spec_set=["children"])
    node.children = [
        _make_subnode("foo", None),
        _make_subnode("bar", drop),
        _make_subnode("baz", null),
    ]
    typ = Mapping()

    result = typ.deserialize(node, cstruct)

    assert result == exp_appstruct


@pytest.mark.parametrize(
    "unknown, appstruct, exp_or_raises",
    [
        ("ignore", "null", {}),
        ("ignore", {}, {}),
        ("ignore", {"foo": "Foo"}, {}),
        ("preserve", {"foo": "Foo"}, {"foo": "Foo"}),
        ("raise", {"foo": "Foo"}, "UnsupportedFields"),
    ],
)
def test_Mapping_serialize_wo_children(unknown, appstruct, exp_or_raises):
    from colander import Mapping
    from colander import UnsupportedFields
    from colander import null

    if appstruct == "null":
        appstruct = null

    node = mock.Mock(spec_set=["children"])
    node.children = []
    typ = Mapping(unknown)

    if exp_or_raises == "UnsupportedFields":
        with pytest.raises(UnsupportedFields):
            typ.serialize(node, appstruct)
    else:
        result = typ.serialize(node, appstruct)

        assert result == exp_or_raises


def test_Mapping_serialize_w_child_wo_default():
    from colander import Invalid
    from colander import Mapping
    from colander import null

    node = mock.Mock(spec_set=["children", "typ"])
    sub = mock.Mock(spec_set=["name", "serialize", "default"])

    sub.name = "foo"
    sub.default = None

    def _assert_not_null(value):
        if value is null:
            raise Invalid(sub)

    sub.serialize = _assert_not_null

    node.children = [sub]
    typ = Mapping()
    appstruct = {}

    with pytest.raises(Invalid):
        typ.serialize(node, appstruct)


@pytest.mark.parametrize(
    "appstruct, exp_cstruct",
    [
        ("null", {"foo": "null", "baz": "null"}),
        ({}, {"foo": "Foo", "baz": "null"}),
        ({"foo": "Foo"}, {"foo": "Foo", "baz": "null"}),
        (
            {"foo": "Foo", "bar": "Bar"},
            {"foo": "Foo", "bar": "Bar", "baz": "null"},
        ),
        (
            {"foo": "Foo", "baz": "Baz"},
            {"foo": "Foo", "baz": "Baz"},
        ),
        (
            {"foo": "Foo", "bar": "Bar", "baz": "Baz"},
            {"foo": "Foo", "bar": "Bar", "baz": "Baz"},
        ),
    ],
)
def test_Mapping_serialize_w_children(appstruct, exp_cstruct):
    from colander import Mapping
    from colander import drop
    from colander import null

    if appstruct == "null":
        appstruct = null

    if exp_cstruct == "null":
        exp_cstruct = null
    else:
        for key, value in list(exp_cstruct.items()):
            if value == "null":
                exp_cstruct[key] = null

    def _make_subnode(name, default):
        sub = mock.Mock(spec_set=["name", "default", "serialize"])
        sub.name = name
        sub.default = default

        if exp_cstruct is not null and name in exp_cstruct:
            sub.serialize.return_value = exp_cstruct[name]
        elif default is null:
            sub.serialize.return_value = null
        else:
            sub.serialize.side_effect = AssertionError

        return sub

    node = mock.Mock(spec_set=["children"])
    node.children = [
        _make_subnode("foo", None),
        _make_subnode("bar", drop),
        _make_subnode("baz", null),
    ]
    typ = Mapping()

    result = typ.serialize(node, appstruct)

    assert result == exp_cstruct


@pytest.mark.parametrize(
    "prefix, listitem",
    [
        (None, None),
        (None, False),
        (None, True),
        ("foo", None),
        ("foo", False),
        ("foo", True),
    ],
)
def test_Mapping_flatten_wo_children(prefix, listitem):
    from colander import Mapping

    node = mock.Mock(spec_set=["name", "children"])
    node.name = NODE_NAME
    node.children = []
    appstruct = mock.Mock(spec_set=())
    typ = Mapping()

    kw = {}

    if prefix is not None:
        kw["prefix"] = prefix

    if listitem is not None:
        kw["listitem"] = listitem

    result = typ.flatten(node, appstruct, **kw)

    assert result == {}


@pytest.mark.parametrize(
    "prefix, listitem, expected",
    [
        (None, None, {"test_node.foo": "Foo", "test_node.bar": "null"}),
        (None, False, {"test_node.foo": "Foo", "test_node.bar": "null"}),
        (None, True, {"foo": "Foo", "bar": "null"}),
        ("foo", None, {"footest_node.foo": "Foo", "footest_node.bar": "null"}),
        (
            "foo",
            False,
            {"footest_node.foo": "Foo", "footest_node.bar": "null"},
        ),
        ("foo", True, {"foofoo": "Foo", "foobar": "null"}),
    ],
)
def test_Mapping_flatten_w_children(prefix, listitem, expected):
    from colander import Mapping
    from colander import SchemaType
    from colander import null

    node = mock.Mock(spec_set=["name", "children"])
    node.name = NODE_NAME

    subnode_1 = mock.Mock(spec_set=["name", "typ"])
    subnode_1.name = "foo"
    subnode_1.typ = SchemaType()

    subnode_2 = mock.Mock(spec_set=["name", "typ"])
    subnode_2.name = "bar"
    subnode_2.typ = SchemaType()

    node.children = [subnode_1, subnode_2]
    appstruct = {"foo": "Foo"}
    typ = Mapping()

    kw = {}

    if prefix is not None:
        kw["prefix"] = prefix

    if listitem is not None:
        kw["listitem"] = listitem

    for key, value in list(expected.items()):
        if value == "null":
            expected[key] = null

    result = typ.flatten(node, appstruct, **kw)

    assert result == expected


def test_Mapping_unflatten():
    from colander import Mapping

    node = mock.Mock(spec_set=())
    paths = []
    fstruct = {}
    typ = Mapping()

    with mock.patch("colander._unflatten_mapping") as um:
        result = typ.unflatten(node, paths, fstruct)

    assert result is um.return_value
    um.assert_called_once_with(node, paths, fstruct)


@pytest.mark.parametrize("node_name", ["", "name"])
def test_Mapping_unflatten_w_node_name(node_name):
    from colander import Mapping

    class Node(dict):
        name = node_name

    node = Node()
    paths = [node_name]
    fstruct = {}
    typ = Mapping()

    result = typ.unflatten(node, paths, fstruct)

    assert result == {}


@pytest.mark.parametrize(
    "path, exp_appstruct",
    [
        ("foo", {"foo": 123, "child": {"grand": {}}}),
        ("child.foo", {"child": {"foo": 123, "grand": {}}}),
        ("child.grand.foo", {"child": {"grand": {"foo": 123}}}),
    ],
)
def test_Mapping_set_value(path, exp_appstruct):
    from colander import Mapping

    class _Node(dict):
        def __init__(self):
            self.typ = Mapping()

    node = _Node()
    child = node["child"] = _Node()
    child.typ = Mapping()
    grand = child["grand"] = _Node()
    grand.typ = Mapping()

    typ = Mapping()
    appstruct = {"child": {"grand": {}}}

    result = typ.set_value(node, appstruct, path, 123)

    assert result == exp_appstruct


@pytest.mark.parametrize(
    "path, expected",
    [
        ("foo", 123),
        ("child.foo", 234),
        ("child.grand.foo", 345),
    ],
)
def test_Mapping_get_value(path, expected):
    from colander import Mapping

    class _Node(dict):
        def __init__(self):
            self.typ = Mapping()

    node = _Node()
    child = node["child"] = _Node()
    child.typ = Mapping()
    grand = child["grand"] = _Node()
    grand.typ = Mapping()

    typ = Mapping()
    appstruct = {"foo": 123, "child": {"foo": 234, "grand": {"foo": 345}}}

    result = typ.get_value(node, appstruct, path)

    assert result == expected


@pytest.mark.parametrize("value", [None, MARKER])
def test_Tuple__validate_not_iterable(value):
    from colander import Invalid
    from colander import Tuple

    node = mock.Mock(spec_set=())
    typ = Tuple()

    with pytest.raises(Invalid) as exc:
        typ._validate(node, value)

    invalid = exc.value
    assert invalid.node is node
    assert isinstance(invalid.msg, translationstring.TranslationString)
    assert invalid.msg.default == '"${val}" is not iterable'
    assert invalid.msg.mapping["val"] is value


@pytest.mark.parametrize("value", [(0, 1, 2), [0, 1, 2]])
def test_Tuple__validate_wrong_length(value):
    from colander import Invalid
    from colander import Tuple

    node = mock.Mock(spec_set=["children"])
    node.children = ["a", "b"]
    typ = Tuple()

    with pytest.raises(Invalid) as exc:
        typ._validate(node, value)

    invalid = exc.value
    assert invalid.node is node
    assert isinstance(invalid.msg, translationstring.TranslationString)
    assert invalid.msg.default == (
        '"${val}" has an incorrect number of elements '
        '(expected ${exp}, was ${was})'
    )
    assert invalid.msg.mapping["val"] is value
    assert invalid.msg.mapping["exp"] == 2
    assert invalid.msg.mapping["was"] == len(value)


@pytest.mark.parametrize("value", [(0, 1, 2), [0, 1, 2]])
def test_Tuple__validate_hit(value):
    from colander import Tuple

    node = mock.Mock(spec_set=["children"])
    node.children = ["a", "b", "c"]
    typ = Tuple()

    result = typ._validate(node, value)

    assert result == list(value)


def test_Tuple_cstruct_children_w_null_wo_children():
    from colander import Tuple
    from colander import null

    node = mock.Mock(spec_set=["children"])
    node.children = []
    typ = Tuple()

    result = typ.cstruct_children(node, null)

    assert result == []


def test_Tuple_cstruct_children_w_null_w_children():
    from colander import Tuple
    from colander import null

    node = mock.Mock(spec_set=["children"])
    subnode = mock.Mock(spec_set=["name", "serialize"])
    subnode.name = "sub"
    node.children = [subnode]
    typ = Tuple()

    result = typ.cstruct_children(node, null)

    assert result == [subnode.serialize.return_value]


def test_Tuple_cstruct_children_w_list_w_fewer_children():
    from colander import Tuple

    node = mock.Mock(spec_set=["children"])
    node.children = ["a"]
    typ = Tuple()

    result = typ.cstruct_children(node, [0, 1, 2])

    assert result == [0]


def test_Tuple_cstruct_children_w_dict_w_more_children():
    from colander import Tuple

    node = mock.Mock(spec_set=["children"])
    node.children = []
    subnode_1 = mock.Mock(spec_set=["name", "serialize"])
    subnode_1.name = "foo"
    subnode_2 = mock.Mock(spec_set=["name", "serialize"])
    subnode_2.name = "bar"
    node.children = [subnode_1, subnode_2]
    typ = Tuple()

    result = typ.cstruct_children(node, [0])

    assert result == [0, subnode_2.serialize.return_value]


def test_Tuple_cstruct_children_w_dict_w_same_num_children():
    from colander import Tuple

    node = mock.Mock(spec_set=["children"])
    node.children = []
    subnode_1 = mock.Mock(spec_set=["name", "serialize"])
    subnode_1.name = "foo"
    subnode_2 = mock.Mock(spec_set=["name", "serialize"])
    subnode_2.name = "bar"
    node.children = [subnode_1, subnode_2]
    typ = Tuple()

    result = typ.cstruct_children(node, [0, 1])

    assert result == [0, 1]


@pytest.mark.parametrize(
    "appstruct, expected",
    [
        ("null", "null"),
        ([], ()),
        ((), ()),
    ],
)
def test_Tuple_serialize_wo_children(appstruct, expected):
    from colander import Tuple
    from colander import null

    if appstruct == "null":
        appstruct = null

    if expected == "null":
        expected = null

    node = mock.Mock(spec_set=["children"])
    node.children = []
    typ = Tuple()

    result = typ.serialize(node, appstruct)

    assert result == expected


@pytest.mark.parametrize(
    "appstruct, expected",
    [
        ("null", "null"),
        ([0, 1], ("a", "b")),
        ((0, 1), ("a", "b")),
    ],
)
def test_Tuple_serialize_w_children(appstruct, expected):
    from colander import Tuple
    from colander import null

    if appstruct == "null":
        appstruct = null

    if expected == "null":
        expected = null

    node = mock.Mock(spec_set=["children"])
    subnode_1 = mock.Mock(spec_set=["serialize"])
    subnode_1.serialize.return_value = "a"
    subnode_2 = mock.Mock(spec_set=["serialize"])
    subnode_2.serialize.return_value = "b"
    node.children = [subnode_1, subnode_2]
    typ = Tuple()

    result = typ.serialize(node, appstruct)

    assert result == expected


def test_Tuple_serialize_w_child_node_raising():
    from colander import Invalid
    from colander import Tuple

    appstruct = [0, 1]
    node = mock.Mock(spec_set=["children", "typ"])
    subnode_1 = mock.Mock(spec_set=["serialize"])
    subnode_1.serialize.return_value = "a"
    subnode_2 = mock.Mock(spec_set=["serialize"])
    subnode_2.serialize.side_effect = Invalid(subnode_2, "testing")
    node.children = [subnode_1, subnode_2]
    typ = node.typ = Tuple()

    with pytest.raises(Invalid) as exc:
        typ.serialize(node, appstruct)

    invalid = exc.value
    assert invalid.node is node
    assert invalid.msg is None

    assert len(invalid.children) == 1
    sub_inv = exc.value.children[0]
    assert sub_inv.node is subnode_2
    assert sub_inv.msg == "testing"


@pytest.mark.parametrize(
    "cstruct, exp_or_raises",
    [
        ("null", "null"),
        ((), ()),
        ([], ()),
    ],
)
def test_Tuple_deserialize_wo_children(cstruct, exp_or_raises):
    from colander import Tuple
    from colander import null

    if cstruct == "null":
        cstruct = null

    if exp_or_raises == "null":
        exp_or_raises = null

    node = mock.Mock(spec_set=["children"])
    node.children = []
    typ = Tuple()

    result = typ.deserialize(node, cstruct)

    assert result == exp_or_raises


@pytest.mark.parametrize(
    "cstruct, expected",
    [
        ("null", "null"),
        ([0, 1], ("a", "b")),
        ((0, 1), ("a", "b")),
    ],
)
def test_Tuple_deserialize_w_children(cstruct, expected):
    from colander import Tuple
    from colander import null

    if cstruct == "null":
        cstruct = null

    if expected == "null":
        expected = null

    node = mock.Mock(spec_set=["children"])
    subnode_1 = mock.Mock(spec_set=["deserialize"])
    subnode_1.deserialize.return_value = "a"
    subnode_2 = mock.Mock(spec_set=["deserialize"])
    subnode_2.deserialize.return_value = "b"
    node.children = [subnode_1, subnode_2]
    typ = Tuple()

    result = typ.deserialize(node, cstruct)

    assert result == expected


def test_Tuple_deserialize_w_child_node_raising():
    from colander import Invalid
    from colander import Tuple

    cstruct = [0, 1]
    node = mock.Mock(spec_set=["children", "typ"])
    subnode_1 = mock.Mock(spec_set=["deserialize"])
    subnode_1.deserialize.return_value = "a"
    subnode_2 = mock.Mock(spec_set=["deserialize"])
    subnode_2.deserialize.side_effect = Invalid(subnode_2, "testing")
    node.children = [subnode_1, subnode_2]
    typ = node.typ = Tuple()

    with pytest.raises(Invalid) as exc:
        typ.deserialize(node, cstruct)

    invalid = exc.value
    assert invalid.node is node
    assert invalid.msg is None

    assert len(invalid.children) == 1
    sub_inv = exc.value.children[0]
    assert sub_inv.node is subnode_2
    assert sub_inv.msg == "testing"


@pytest.mark.parametrize(
    "prefix, listitem",
    [
        (None, None),
        (None, False),
        (None, True),
        ("foo", None),
        ("foo", False),
        ("foo", True),
    ],
)
def test_Tuple_flatten_wo_children(prefix, listitem):
    from colander import Tuple

    node = mock.Mock(spec_set=["name", "children"])
    node.name = NODE_NAME
    node.children = []
    appstruct = mock.Mock(spec_set=())
    typ = Tuple()

    kw = {}

    if prefix is not None:
        kw["prefix"] = prefix

    if listitem is not None:
        kw["listitem"] = listitem

    result = typ.flatten(node, appstruct, **kw)

    assert result == {}


@pytest.mark.parametrize(
    "prefix, listitem, expected",
    [
        (None, None, {"test_node.foo": 0, "test_node.bar": 1}),
        (None, False, {"test_node.foo": 0, "test_node.bar": 1}),
        (None, True, {"foo": 0, "bar": 1}),
        ("foo", None, {"footest_node.foo": 0, "footest_node.bar": 1}),
        (
            "foo",
            False,
            {"footest_node.foo": 0, "footest_node.bar": 1},
        ),
        ("foo", True, {"foofoo": 0, "foobar": 1}),
    ],
)
def test_Tuple_flatten_w_children(prefix, listitem, expected):
    from colander import SchemaType
    from colander import Tuple
    from colander import null

    node = mock.Mock(spec_set=["name", "children"])
    node.name = NODE_NAME

    subnode_1 = mock.Mock(spec_set=["name", "typ"])
    subnode_1.name = "foo"
    subnode_1.typ = SchemaType()

    subnode_2 = mock.Mock(spec_set=["name", "typ"])
    subnode_2.name = "bar"
    subnode_2.typ = SchemaType()

    node.children = [subnode_1, subnode_2]
    appstruct = [0, 1]
    typ = Tuple()

    kw = {}

    if prefix is not None:
        kw["prefix"] = prefix

    if listitem is not None:
        kw["listitem"] = listitem

    for key, value in list(expected.items()):
        if value == "null":
            expected[key] = null

    result = typ.flatten(node, appstruct, **kw)

    assert result == expected


def test_Tuple_unflatten_wo_children():
    from colander import Tuple

    node = mock.Mock(spec_set=["children"])
    node.children = []
    paths = []
    fstruct = {}
    typ = Tuple()

    with mock.patch("colander._unflatten_mapping") as um:
        um.return_value = {}
        result = typ.unflatten(node, paths, fstruct)

    assert result == ()
    um.assert_called_once_with(node, paths, fstruct)


def test_Tuple_unflatten_w_children():
    from colander import Tuple

    node = mock.Mock(spec_set=["children"])
    subnode_1 = mock.Mock(spec_set=["name"])
    subnode_1.name = "foo"
    subnode_2 = mock.Mock(spec_set=["name"])
    subnode_2.name = "bar"
    node.children = [subnode_1, subnode_2]
    paths = []
    fstruct = {}
    typ = Tuple()

    with mock.patch("colander._unflatten_mapping") as um:
        um.return_value = {"foo": 0, "bar": 1}
        result = typ.unflatten(node, paths, fstruct)

    assert result == (0, 1)
    um.assert_called_once_with(node, paths, fstruct)


@pytest.mark.parametrize("node_name", ["", "name"])
def test_Tuple_unflatten_w_node_name(node_name):
    from colander import Tuple

    class Node(dict):
        name = node_name
        children = ()

    node = Node()
    paths = [node_name]
    fstruct = {}
    typ = Tuple()

    result = typ.unflatten(node, paths, fstruct)

    assert result == ()


@pytest.mark.parametrize(
    "path, exp_appstruct",
    [
        ("foo", (123, (3, 4))),
        ("foo.a", ((123, 2), (3, 4))),
        ("foo.b", ((1, 123), (3, 4))),
        ("foo.c", "KeyError"),
        ("bar", ((1, 2), 123)),
        ("bar.c", ((1, 2), (123, 4))),
        ("bar.d", ((1, 2), (3, 123))),
        ("bar.a", "KeyError"),
        ("baz", "KeyError"),
    ],
)
def test_Tuple_set_value(path, exp_appstruct):
    from colander import SchemaType
    from colander import Tuple

    class _Node(dict):
        def __init__(self, name, typ):
            self.name = name
            self.typ = typ

        @property
        def children(self):
            return self.values()

    node = _Node("root", Tuple())
    node["foo"] = _Node("foo", Tuple())
    node["foo"]["a"] = _Node("a", SchemaType())
    node["foo"]["b"] = _Node("b", SchemaType())
    node["bar"] = _Node("bar", Tuple())
    node["bar"]["c"] = _Node("c", SchemaType())
    node["bar"]["d"] = _Node("d", SchemaType())

    typ = Tuple()
    appstruct = ((1, 2), (3, 4))

    if exp_appstruct == "KeyError":

        with pytest.raises(KeyError):
            typ.set_value(node, appstruct, path, 123)

    else:
        result = typ.set_value(node, appstruct, path, 123)
        assert result == exp_appstruct


@pytest.mark.parametrize(
    "path, exp_value",
    [
        ("foo", (1, 2)),
        ("foo.a", 1),
        ("foo.b", 2),
        ("foo.c", "KeyError"),
        ("bar", (3, 4)),
        ("bar.c", 3),
        ("bar.d", 4),
        ("bar.a", "KeyError"),
        ("baz", "KeyError"),
    ],
)
def test_Tuple_get_value(path, exp_value):
    from colander import SchemaType
    from colander import Tuple

    class _Node(dict):
        def __init__(self, name, typ):
            self.name = name
            self.typ = typ

        @property
        def children(self):
            return self.values()

    node = _Node("root", Tuple())
    node["foo"] = _Node("foo", Tuple())
    node["foo"]["a"] = _Node("a", SchemaType())
    node["foo"]["b"] = _Node("b", SchemaType())
    node["bar"] = _Node("bar", Tuple())
    node["bar"]["c"] = _Node("c", SchemaType())
    node["bar"]["d"] = _Node("d", SchemaType())

    typ = Tuple()
    appstruct = ((1, 2), (3, 4))

    if exp_value == "KeyError":

        with pytest.raises(KeyError):
            typ.get_value(node, appstruct, path)

    else:
        result = typ.get_value(node, appstruct, path)
        assert result == exp_value


@pytest.mark.parametrize(
    "appstruct",
    [
        "null",
        [],
        (),
        [0, 1, 2],
        (3, 4, 5),
    ],
)
def test_Set_serialize(appstruct):
    from colander import Set
    from colander import null

    if appstruct == "null":
        appstruct = null

    node = mock.Mock(spec_set=())
    typ = Set()

    result = typ.serialize(node, appstruct)

    assert result == appstruct


@pytest.mark.parametrize(
    "cstruct, expected",
    [
        ("null", "null"),
        ([], set()),
        ((), set()),
        ([0, 1, 2], set([0, 1, 2])),
        ((3, 4, 5), set([3, 4, 5])),
        ("foo", "Invalid"),
        (MARKER, "Invalid"),
    ],
)
def test_Set_deserialize(cstruct, expected):
    from colander import Invalid
    from colander import Set
    from colander import null

    if cstruct == "null":
        cstruct = null

    if expected == "null":
        expected = null

    node = mock.Mock(spec_set=())
    typ = Set()

    if expected == "Invalid":

        with pytest.raises(Invalid) as exc:
            typ.deserialize(node, cstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == '${cstruct} is not iterable'
        assert invalid.msg.mapping["cstruct"] is cstruct
    else:
        result = typ.deserialize(node, cstruct)
        assert result == expected


@pytest.mark.parametrize(
    "appstruct",
    [
        "null",
        [],
        (),
        [0, 1, 2],
        (3, 4, 5),
    ],
)
def test_List_serialize(appstruct):
    from colander import List
    from colander import null

    if appstruct == "null":
        appstruct = null

    node = mock.Mock(spec_set=())
    typ = List()

    result = typ.serialize(node, appstruct)

    assert result == appstruct


@pytest.mark.parametrize(
    "cstruct, expected",
    [
        ("null", "null"),
        ([], []),
        ((), []),
        ([0, 1, 2], [0, 1, 2]),
        ((3, 4, 5), [3, 4, 5]),
        ("foo", "Invalid"),
        (MARKER, "Invalid"),
    ],
)
def test_List_deserialize(cstruct, expected):
    from colander import Invalid
    from colander import List
    from colander import null

    if cstruct == "null":
        cstruct = null

    if expected == "null":
        expected = null

    node = mock.Mock(spec_set=())
    typ = List()

    if expected == "Invalid":

        with pytest.raises(Invalid) as exc:
            typ.deserialize(node, cstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == '${cstruct} is not iterable'
        assert invalid.msg.mapping["cstruct"] is cstruct
    else:
        result = typ.deserialize(node, cstruct)
        assert result == expected


@pytest.mark.parametrize("accept_scalar", [None, False, True])
def test_Sequence_ctor(accept_scalar):
    from colander import Sequence

    if accept_scalar is None:
        typ = Sequence()
    else:
        typ = Sequence(accept_scalar=accept_scalar)

    assert typ.accept_scalar == bool(accept_scalar)


@pytest.mark.parametrize(
    "accept_scalar, value, expected",
    [
        (False, (), []),
        (False, (1, 2), [1, 2]),
        (False, set(), []),
        (False, set([1, 2]), [1, 2]),
        (False, [], []),
        (False, [1, 2], [1, 2]),
        (False, b"foo", [ord(b"f"), ord(b"o"), ord(b"o")]),
        (False, MARKER, "Invalid"),
        (False, "foo", "Invalid"),
        (False, {"foo": "Foo"}, "Invalid"),
        (True, (), []),
        (True, (1, 2), [1, 2]),
        (True, set(), []),
        (True, set([1, 2]), [1, 2]),
        (True, [], []),
        (True, [1, 2], [1, 2]),
        (True, b"foo", [ord(b"f"), ord(b"o"), ord(b"o")]),
        (True, MARKER, [MARKER]),
        (True, "foo", ["foo"]),
        (True, {"foo": "Foo"}, [{"foo": "Foo"}]),
    ],
)
def test_Sequence__validate(accept_scalar, value, expected):
    from colander import Invalid
    from colander import Sequence

    node = mock.Mock(spec_set=())
    typ = Sequence()

    if expected == "Invalid":

        with pytest.raises(Invalid) as exc:
            typ._validate(node, value, accept_scalar)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == '"${val}" is not iterable'
        assert invalid.msg.mapping["val"] is value

    else:
        assert typ._validate(node, value, accept_scalar) == expected


@pytest.mark.parametrize(
    "cstruct, expected_list",
    [
        ("null", []),
        ((), []),
        ((1, 2), [1, 2]),
        (set(), []),
        (set([1, 2]), [1, 2]),
        ([], []),
        ([1, 2], [1, 2]),
        (b"foo", [ord(b"f"), ord(b"o"), ord(b"o")]),
    ],
)
def test_Sequence_cstruct_children(cstruct, expected_list):
    from colander import Sequence
    from colander import SequenceItems
    from colander import null

    if cstruct == "null":
        cstruct = null

    node = mock.Mock(spec_set=())
    typ = Sequence()

    result = typ.cstruct_children(node, cstruct)

    assert isinstance(result, SequenceItems)
    assert result == expected_list


@pytest.mark.parametrize(
    "accept_scalar, default, appstruct, exp_cstruct",
    [
        (None, None, "null", "null"),
        (None, None, [], []),
        (None, None, [0, 1], ["0", "1"]),
        (None, None, ["drop"], []),
        (None, None, ["null"], ["null"]),
        (None, "drop", ["null"], []),
        (None, "drop", [0, "null", 1], ["0", "1"]),
        (True, None, 0, ["0"]),
    ],
)
def test_Sequence_serialize(
    accept_scalar,
    default,
    appstruct,
    exp_cstruct,
):
    from colander import Integer
    from colander import Sequence
    from colander import drop
    from colander import null

    _converters = {
        "drop": drop,
        "null": null,
    }

    if default == "drop":
        default = drop

    if appstruct == "null":
        appstruct = null
    else:
        appstruct = [_converters.get(value, value) for value in exp_cstruct]

    if exp_cstruct == "null":
        exp_cstruct = null
    else:
        exp_cstruct = [_converters.get(value, value) for value in exp_cstruct]

    int_type = Integer()

    def _make_subnode(default):
        sub = mock.Mock(spec_set=["typ", "default", "serialize"])
        sub.typ = Integer
        sub.default = default
        sub.serialize = lambda appstruct: int_type.serialize(sub, appstruct)
        return sub

    node = mock.Mock(spec_set=["children"])
    node.children = [
        _make_subnode(default),
    ]
    typ = Sequence()

    if accept_scalar is not None:
        result = typ.serialize(node, appstruct, accept_scalar=accept_scalar)
    else:
        result = typ.serialize(node, appstruct)

    assert result == exp_cstruct


@pytest.mark.parametrize(
    "accept_scalar, missing, cstruct, exp_appstruct",
    [
        (None, None, "null", "null"),
        (None, None, [], []),
        (None, None, ["0", "1"], [0, 1]),
        (None, None, ["drop"], []),
        (None, None, ["subdrop"], []),
        (None, None, ["null"], ["null"]),
        (None, "drop", ["null"], []),
        (None, "drop", ["0", "null", "1"], [0, 1]),
        (True, None, "0", [0]),
    ],
)
def test_Sequence_deserialize(
    accept_scalar,
    missing,
    cstruct,
    exp_appstruct,
):
    from colander import Integer
    from colander import Sequence
    from colander import drop
    from colander import null

    _converters = {
        "drop": drop,
        "null": null,
    }

    if missing == "drop":
        missing = drop

    if cstruct == "null":
        cstruct = null
    else:
        cstruct = [_converters.get(value, value) for value in cstruct]

    if exp_appstruct == "null":
        exp_appstruct = null
    else:
        exp_appstruct = [
            _converters.get(value, value) for value in exp_appstruct
        ]

    int_type = Integer()

    def _subnode_deserialize(cstruct):
        if cstruct == "subdrop":
            return drop
        return int_type.deserialize(None, cstruct)

    def _make_subnode(missing):
        sub = mock.Mock(spec_set=["typ", "missing", "deserialize"])
        sub.typ = Integer
        sub.missing = missing
        sub.deserialize = _subnode_deserialize
        return sub

    node = mock.Mock(spec_set=["children"])
    node.children = [
        _make_subnode(missing),
    ]
    typ = Sequence()

    if accept_scalar is not None:
        result = typ.deserialize(node, cstruct, accept_scalar=accept_scalar)
    else:
        result = typ.deserialize(node, cstruct)

    assert result == exp_appstruct


@pytest.mark.parametrize(
    "prefix, listitem, expected",
    [
        (None, None, {"test.0": "bar", "test.1": "null"}),
        (None, False, {"test.0": "bar", "test.1": "null"}),
        (None, True, {"0": "bar", "1": "null"}),
        ("foo", None, {"footest.0": "bar", "footest.1": "null"}),
        ("foo", False, {"footest.0": "bar", "footest.1": "null"}),
        ("foo", True, {"foo0": "bar", "foo1": "null"}),
    ],
)
def test_Sequence_flatten(prefix, listitem, expected):
    from colander import SchemaType
    from colander import Sequence
    from colander import null

    node = mock.Mock(spec_set=["name", "children"])
    node.name = "test"
    subnode_1 = mock.Mock(spec_set=["name", "typ"])
    subnode_1.name = "foo"
    subnode_1.typ = SchemaType()
    node.children = [subnode_1]

    appstruct = ["bar", null]
    typ = Sequence()

    kw = {}

    if prefix is not None:
        kw["prefix"] = prefix

    if listitem is not None:
        kw["listitem"] = listitem

    for key, value in list(expected.items()):
        if value == "null":
            expected[key] = null

    result = typ.flatten(node, appstruct, **kw)

    assert result == expected


def test_Sequence_unflatten():
    from colander import Sequence

    node = mock.Mock(spec_set=["children"])
    subnode_1 = mock.Mock(spec_set=["name"])
    subnode_1.name = "foo"
    node.children = [subnode_1]

    paths = []
    fstruct = {}
    typ = Sequence()

    with mock.patch("colander._unflatten_mapping") as um:
        um.return_value = {"0": 0, "1": 1}
        result = typ.unflatten(node, paths, fstruct)

    assert result == [0, 1]
    um.assert_called_once_with(node, paths, fstruct, mock.ANY, mock.ANY)
    _, _, _, g_c, r_s = um.call_args_list[0].args

    assert g_c("foo") is subnode_1
    assert r_s("waaa.blah") == "foo.blah"
    assert r_s("waaa") == "foo"


@pytest.mark.parametrize("node_name", ["", "name"])
def test_Sequence_unflatten_w_node_name(node_name):
    from colander import Sequence

    child = mock.Mock(spec_set=["name"])
    child.name = "child"

    class Node(dict):
        name = node_name
        children = [child]

    node = Node()
    paths = [node_name]
    fstruct = {}
    typ = Sequence()

    result = typ.unflatten(node, paths, fstruct)

    assert result == []


@pytest.mark.parametrize(
    "path, exp_appstruct",
    [
        ("0", [123, [3, 4]]),
        ("0.0", [[123, 2], [3, 4]]),
        ("0.1", [[1, 123], [3, 4]]),
        ("0.2", "IndexError"),
        ("1", [[1, 2], 123]),
        ("1.0", [[1, 2], [123, 4]]),
        ("1.1", [[1, 2], [3, 123]]),
        ("1.2", "IndexError"),
        ("2", "IndexError"),
    ],
)
def test_Sequence_set_value(path, exp_appstruct):
    from colander import Integer
    from colander import Sequence

    class _Node(dict):
        def __init__(self, name, typ):
            self.name = name
            self.typ = typ

        @property
        def children(self):
            return list(self.values())

    node = _Node("root", Sequence())
    node["0"] = _Node("foo", Sequence())
    node["0"]["0"] = _Node("a", Integer())
    node["1"] = _Node("bar", Sequence())
    node["1"]["0"] = _Node("c", Integer())

    typ = Sequence()
    appstruct = [[1, 2], [3, 4]]

    if exp_appstruct == "IndexError":

        with pytest.raises(IndexError):
            typ.set_value(node, appstruct, path, 123)

    else:
        result = typ.set_value(node, appstruct, path, 123)
        assert result == exp_appstruct


@pytest.mark.parametrize(
    "path, exp_value",
    [
        ("0", [1, 2]),
        ("0.0", 1),
        ("0.1", 2),
        ("0.2", "IndexError"),
        ("1", [3, 4]),
        ("1.0", 3),
        ("1.1", 4),
        ("1.2", "IndexError"),
        ("2", "IndexError"),
    ],
)
def test_Sequence_get_value(path, exp_value):
    from colander import Integer
    from colander import Sequence

    class _Node(dict):
        def __init__(self, name, typ):
            self.name = name
            self.typ = typ

        @property
        def children(self):
            return list(self.values())

    node = _Node("root", Sequence())
    node["0"] = _Node("0", Sequence())
    node["0"]["0"] = _Node("0", Integer())
    node["1"] = _Node("1", Sequence())
    node["1"]["0"] = _Node("c", Integer())

    typ = Sequence()
    appstruct = [[1, 2], [3, 4]]

    if exp_value == "IndexError":

        with pytest.raises(IndexError):
            typ.get_value(node, appstruct, path)

    else:
        result = typ.get_value(node, appstruct, path)
        assert result == exp_value


@pytest.mark.parametrize("allow_empty", [None, False, True])
@pytest.mark.parametrize("encoding", [None, "utf8"])
def test_String_ctor(encoding, allow_empty):
    from colander import String

    kw = {}

    if encoding is not None:
        kw["encoding"] = encoding

    if allow_empty is not None:
        kw["allow_empty"] = allow_empty

    typ = String(**kw)

    assert typ.encoding == encoding
    assert typ.allow_empty == bool(allow_empty)


class Uncooperative:
    def __str__(self):
        raise ValueError('I wont cooperate')


@pytest.mark.parametrize(
    "encoding, appstruct, expected",
    [
        (None, "null", "null"),
        (None, "", ""),
        (None, "abc", "abc"),
        (None, 0, "0"),
        (None, MARKER, str(MARKER)),
        (None, Uncooperative(), "Invalid"),
        ("utf-8", UNI, UTF8),
        ("utf-8", 123, b"123"),
        ("utf-16", UNI, UTF16),
    ],
)
def test_String_serialize(encoding, appstruct, expected):
    from colander import Invalid
    from colander import String
    from colander import null

    node = mock.Mock(spec_set=())
    typ = String(encoding)

    if appstruct == "null":
        appstruct = null

    if expected == "null":
        expected = null

    if expected == "Invalid":

        with pytest.raises(Invalid) as exc:
            typ.serialize(node, appstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == '${val} cannot be serialized: ${err}'
        assert invalid.msg.mapping["val"] is appstruct

    else:
        result = typ.serialize(node, appstruct)
        assert result == expected


@pytest.mark.parametrize(
    "encoding, allow_empty, cstruct, expected",
    [
        (None, False, "null", "null"),
        (None, False, "", "null"),
        (None, True, "", ""),
        (None, False, "abc", "abc"),
        (None, False, MARKER, "Invalid"),
        ("ascii", False, b"123", "123"),
        ("utf-8", False, b"123", "123"),
        ("utf-8", False, UTF8, UNI),
        ("utf-16", False, UTF16, UNI),
    ],
)
def test_String_deserialize(encoding, allow_empty, cstruct, expected):
    from colander import Invalid
    from colander import String
    from colander import null

    node = mock.Mock(spec_set=())
    kw = {}

    if encoding is not None:
        kw["encoding"] = encoding

    if cstruct == "null":
        cstruct = null

    if expected == "null":
        expected = null

    if allow_empty is not None:
        kw["allow_empty"] = allow_empty

    typ = String(**kw)

    if expected == "Invalid":

        with pytest.raises(Invalid) as exc:
            typ.deserialize(node, cstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == '${val} is not a string: ${err}'
        assert invalid.msg.mapping["val"] is cstruct

    else:
        result = typ.deserialize(node, cstruct)
        assert result == expected


@pytest.mark.parametrize(
    "appstruct, expected",
    [
        ("null", "null"),
        (0, "0"),
        (-1, "-1"),
        (3, "Invalid"),
        (2.71828, "2"),
    ],
)
def test_Number_serialize(appstruct, expected):
    from colander import Invalid
    from colander import Number
    from colander import null

    def _anything_but_3(val):
        assert val != 3
        return int(val)

    node = mock.Mock(spec_set=())
    typ = Number()
    typ.num = _anything_but_3

    if appstruct == "null":
        appstruct = null

    if expected == "null":
        expected = null

    if expected == "Invalid":

        with pytest.raises(Invalid) as exc:
            typ.serialize(node, appstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == '"${val}" is not a number'
        assert invalid.msg.mapping["val"] is appstruct

    else:
        result = typ.serialize(node, appstruct)
        assert result == expected


@pytest.mark.parametrize(
    "cstruct, expected",
    [
        ("null", "null"),
        ("", "null"),
        ("0", 0),
        ("-1", -1),
        ("2", 2),
        ("3", "Invalid"),
    ],
)
def test_Number_deserialize(cstruct, expected):
    from colander import Invalid
    from colander import Number
    from colander import null

    def _anything_but_3(val):
        assert val != "3"
        return int(val)

    node = mock.Mock(spec_set=())
    typ = Number()
    typ.num = _anything_but_3

    if cstruct == "null":
        cstruct = null

    if expected == "null":
        expected = null

    if expected == "Invalid":

        with pytest.raises(Invalid) as exc:
            typ.deserialize(node, cstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == '"${val}" is not a number'
        assert invalid.msg.mapping["val"] is cstruct

    else:
        result = typ.deserialize(node, cstruct)
        assert result == expected


@pytest.mark.parametrize(
    "value, raises",
    [
        (0, False),
        (0.0, False),
        (-1, False),
        (-1.0, False),
        (2.71828, True),
    ],
)
def test_Integer_ctor_strict(value, raises):
    from colander import Integer

    typ = Integer(strict=True)

    if raises:

        with pytest.raises(ValueError) as exc:
            typ.num(value)

        verr = exc.value
        assert verr.args[0] == "Value is not an Integer"
    else:
        typ.num(value)  # no raise


@pytest.mark.parametrize(
    "appstruct, expected",
    [
        ("null", "null"),
        (0, "0"),
        (-1, "-1"),
        (2.71828, "2"),
    ],
)
def test_Integer_serialize(appstruct, expected):
    from colander import Integer
    from colander import Invalid
    from colander import null

    node = mock.Mock(spec_set=())
    typ = Integer()

    if appstruct == "null":
        appstruct = null

    if expected == "null":
        expected = null

    if expected == "Invalid":

        with pytest.raises(Invalid) as exc:
            typ.serialize(node, appstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == '"${val}" is not a number'
        assert invalid.msg.mapping["val"] is appstruct

    else:
        result = typ.serialize(node, appstruct)
        assert result == expected


@pytest.mark.parametrize(
    "cstruct, expected",
    [
        ("null", "null"),
        ("", "null"),
        ("0", 0),
        ("-1", -1),
        ("2", 2),
        (MARKER, "Invalid"),
    ],
)
def test_Integer_deserialize(cstruct, expected):
    from colander import Integer
    from colander import Invalid
    from colander import null

    node = mock.Mock(spec_set=())
    typ = Integer()

    if cstruct == "null":
        cstruct = null

    if expected == "null":
        expected = null

    if expected == "Invalid":

        with pytest.raises(Invalid) as exc:
            typ.deserialize(node, cstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == '"${val}" is not a number'
        assert invalid.msg.mapping["val"] is cstruct

    else:
        result = typ.deserialize(node, cstruct)
        assert result == expected


@pytest.mark.parametrize(
    "appstruct, expected",
    [
        ("null", "null"),
        (0, "0.0"),
        (-1, "-1.0"),
        (2.71828, "2.71828"),
        (MARKER, "Invalid"),
    ],
)
def test_Float_serialize(appstruct, expected):
    from colander import Float
    from colander import Invalid
    from colander import null

    node = mock.Mock(spec_set=())
    typ = Float()

    if appstruct == "null":
        appstruct = null

    if expected == "null":
        expected = null

    if expected == "Invalid":

        with pytest.raises(Invalid) as exc:
            typ.serialize(node, appstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == '"${val}" is not a number'
        assert invalid.msg.mapping["val"] is appstruct

    else:
        result = typ.serialize(node, appstruct)
        assert result == expected


@pytest.mark.parametrize(
    "cstruct, expected",
    [
        ("null", "null"),
        ("", "null"),
        ("0", 0.0),
        ("-1", -1),
        ("2.71828", 2.71828),
    ],
)
def test_Float_deserialize(cstruct, expected):
    from colander import Float
    from colander import Invalid
    from colander import null

    node = mock.Mock(spec_set=())
    typ = Float()

    if cstruct == "null":
        cstruct = null

    if expected == "null":
        expected = null

    if expected == "Invalid":

        with pytest.raises(Invalid) as exc:
            typ.deserialize(node, cstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == '"${val}" is not a number'
        assert invalid.msg.mapping["val"] is cstruct

    else:
        result = typ.deserialize(node, cstruct)
        assert result == expected


@pytest.mark.parametrize(
    "quant, rounding, normalize",
    [
        (None, None, None),
        ("1.000", None, None),
        ("1.000", "ROUND_UP", False),
        ("1.000", "ROUND_DOWN", True),
    ],
)
def test_Decimal_ctor(quant, rounding, normalize):
    import decimal

    from colander import Decimal

    kw = {}

    if quant is not None:
        kw["quant"] = quant

    if rounding is not None:
        kw["rounding"] = getattr(decimal, rounding)

    if normalize is not None:
        kw["normalize"] = normalize

    typ = Decimal(**kw)

    if quant is None:
        assert typ.quant is None
    else:
        assert typ.quant == decimal.Decimal(quant)

    if rounding is None:
        assert typ.rounding is None
    else:
        assert typ.rounding == kw["rounding"]

    assert typ.normalize == bool(normalize)


@pytest.mark.parametrize(
    "value, quant, rounding, normalize, expected",
    [
        ("pi", None, None, None, "value"),
        ("pi", "1.00", None, None, "3.14"),
        ("pi", "1.00", "ROUND_UP", None, "3.15"),
        ("1.10", None, None, True, "1.1"),
    ],
)
def test_Decimal_num(value, quant, rounding, normalize, expected):
    import decimal
    import math

    from colander import Decimal

    if value == "pi":
        value = math.pi

    if expected == "value":
        expected = decimal.Decimal(str(value))
    else:
        expected = decimal.Decimal(expected)

    kw = {}

    if quant is not None:
        kw["quant"] = quant

    if rounding is not None:
        kw["rounding"] = rounding

    if normalize is not None:
        kw["normalize"] = normalize

    typ = Decimal(**kw)

    result = typ.num(value)

    assert result == expected


def test_Money_ctor():
    import decimal

    from colander import Money

    typ = Money()

    assert typ.quant == decimal.Decimal("0.01")
    assert typ.rounding == decimal.ROUND_UP


@pytest.mark.parametrize(
    "false_chx, true_chx, false_val, true_val",
    [
        (None, None, None, None),
        (("F", "N"), ("T", "Y"), "False", "True"),
    ],
)
def test_Boolean_ctor(false_chx, true_chx, false_val, true_val):
    from colander import Boolean

    kw = {}

    if false_chx is not None:
        exp_false_chx = kw["false_choices"] = false_chx
    else:
        exp_false_chx = ('false', '0')

    if true_chx is not None:
        exp_true_chx = kw["true_choices"] = true_chx
    else:
        exp_true_chx = ()

    if false_val is not None:
        exp_false_val = kw["false_val"] = false_val
    else:
        exp_false_val = "false"

    if true_val is not None:
        exp_true_val = kw["true_val"] = true_val
    else:
        exp_true_val = "true"

    typ = Boolean(**kw)

    assert typ.false_choices == exp_false_chx
    assert typ.false_val == exp_false_val
    assert typ.true_choices == exp_true_chx
    assert typ.true_val == exp_true_val


@pytest.mark.parametrize(
    "appstruct, false_val, true_val, exp_cstruct",
    [
        ("null", None, None, "null"),
        (False, None, None, "false"),
        (None, None, None, "false"),
        (0, "nope", None, "nope"),
        (True, None, None, "true"),
        (1, None, "yep", "yep"),
    ],
)
def test_Boolean_serialize(appstruct, false_val, true_val, exp_cstruct):
    from colander import Boolean
    from colander import null

    kw = {}

    if false_val is not None:
        kw["false_val"] = false_val

    if true_val is not None:
        kw["true_val"] = true_val

    if appstruct == "null":
        appstruct = null

    if exp_cstruct == "null":
        exp_cstruct = null

    typ = Boolean(**kw)
    node = mock.Mock(spec_set=())

    result = typ.serialize(node, appstruct)
    assert result == exp_cstruct


@pytest.mark.parametrize(
    "cstruct, false_chx, true_chx, exp_appstruct",
    [
        ("null", None, None, "null"),
        (False, None, None, False),
        ("false", None, None, False),
        (0, None, None, False),
        ("0", None, None, False),
        ("nope", ("0", "nope"), None, False),
        (True, None, None, True),
        ("1", None, None, True),
        ("yep", None, None, True),
        ("1", None, ("1", "yep"), True),
        ("yep", None, ("1", "yep"), True),
        ("yep", None, ("1", "true"), "Invalid"),
        (Uncooperative(), None, None, "Invalid"),
    ],
)
def test_Boolean_deserialize(cstruct, false_chx, true_chx, exp_appstruct):
    from colander import Boolean
    from colander import Invalid
    from colander import null

    kw = {}

    if false_chx is not None:
        kw["false_choices"] = false_chx

    if true_chx is not None:
        kw["true_choices"] = true_chx

    if cstruct == "null":
        cstruct = null

    if exp_appstruct == "null":
        exp_appstruct = null

    typ = Boolean(**kw)
    node = mock.Mock(spec_set=())

    if exp_appstruct == "Invalid":

        with pytest.raises(Invalid) as exc:
            typ.deserialize(node, cstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)

        assert invalid.msg.mapping["val"] is cstruct

        if len(invalid.msg.mapping) == 1:
            assert invalid.msg.default == '${val} is not a string'
        else:
            assert invalid.msg.default == (
                '"${val}" is neither in (${false_choices}) '
                'nor in (${true_choices})'
            )

    else:
        result = typ.deserialize(node, cstruct)
        assert result == exp_appstruct


@pytest.mark.parametrize("package", [None, pytest])
def test_GlobalObject_ctor(package):
    from colander import GlobalObject

    typ = GlobalObject(package)

    assert typ.package is package


@pytest.mark.parametrize(
    "appstruct, expected",
    [
        ("null", "null"),
        (MARKER, "Unnamed"),
        ("tests", "tests"),
        ("relative", "tests.relative"),
        ("ImportableClass", "tests.relative.ImportableClass"),
        ("importable_func", "tests.relative.importable_func"),
    ],
)
def test_GlobalObject_serialize(appstruct, expected):
    from colander import GlobalObject
    from colander import Invalid
    from colander import null
    import tests
    from tests import relative

    if appstruct == "null":
        appstruct = null
    elif appstruct == "tests":
        appstruct = tests
    elif appstruct == "relative":
        appstruct = relative
    elif appstruct == "ImportableClass":
        appstruct = relative.ImportableClass
    elif appstruct == "importable_func":
        appstruct = relative.importable_func

    if expected == "null":
        expected = null

    typ = GlobalObject(None)
    node = mock.Mock(spec_set=())

    if expected == "Unnamed":

        with pytest.raises(Invalid) as exc:
            typ.serialize(node, appstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == '"${val}" has no __name__'
        assert invalid.msg.mapping["val"] == appstruct

    else:
        result = typ.serialize(node, appstruct)
        assert result == expected


@pytest.mark.parametrize(
    "package, cstruct, expected",
    [
        (None, "null", "null"),
        (None, MARKER, "Nonstring"),
        (None, "tests.nonesuch", "ImportError"),
        (None, "tests:nonesuch", "ImportError"),
        (None, ".", "Irresolvable"),
        (None, ":", "Irresolvable"),
        (None, ".relative.ImportableClass", "Irresolvable"),
        (None, ".relative:ImportableClass", "Irresolvable"),
        (None, "pytest.skip", pytest.skip),
        (None, "pytest:skip", pytest.skip),
        (None, "tests.relative.ImportableClass", "Importable"),
        (None, "tests.relative:ImportableClass", "Importable"),
        ("tests", "pytest.skip", pytest.skip),
        ("tests", "pytest:skip", pytest.skip),
        ("tests", ".", "tests"),
        ("tests", ":", "tests"),
        ("tests", ".relative", "relative"),
        ("tests", ":relative", "relative"),
        ("tests", "..tests.relative", "relative"),
        ("tests", ".relative.ImportableClass", "Importable"),
        ("tests", "..tests.relative.ImportableClass", "Importable"),
        ("tests", ".relative:ImportableClass", "Importable"),
        ("relative", ".", "relative"),
        ("relative", ":", "relative"),
        ("relative", ".ImportableClass", "Importable"),
        ("relative", "..relative.ImportableClass", "Importable"),
        ("relative", "...tests.relative.ImportableClass", "Importable"),
        ("relative", ":ImportableClass", "Importable"),
    ],
)
def test_GlobalObject_deserialize(package, cstruct, expected):
    from colander import GlobalObject
    from colander import Invalid
    from colander import null
    import tests
    from tests import relative

    _GLOBAL_MSG_TEMPLATES = {
        "Nonstring": '"${val}" is not a string',
        "ImportError": 'The dotted name "${name}" cannot be imported',
        "Irresolvable": (
            'relative name "${val}" irresolveable without package'
        ),
    }

    if package == "tests":
        package = tests
    elif package == "relative":
        package = relative

    if cstruct == "null":
        cstruct = null

    if expected == "null":
        expected = null
    elif expected == "tests":
        expected = tests
    elif expected == "relative":
        expected = relative
    elif expected == "Importable":
        expected = relative.ImportableClass

    typ = GlobalObject(package)
    node = mock.Mock(spec_set=())

    if expected in ("Nonstring", "ImportError", "Irresolvable"):

        with pytest.raises(Invalid) as exc:
            typ.deserialize(node, cstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)

        assert invalid.msg.default == _GLOBAL_MSG_TEMPLATES[expected]

        if expected == "ImportError":
            assert invalid.msg.mapping["name"] is cstruct
        else:
            assert invalid.msg.mapping["val"] is cstruct

    else:
        result = typ.deserialize(node, cstruct)
        assert result is expected


@pytest.mark.parametrize("dtz", [None, "GMT_4"])
@pytest.mark.parametrize("fmt", [None, "%c"])
def test_DateTime_ctor(dtz, fmt):
    import iso8601

    from colander import DateTime

    GMT_4 = iso8601.FixedOffset(-4, 0, "GMT-4")

    kw = {}

    if dtz == "GMT_4":
        dtz = GMT_4

    if dtz is not None:
        exp_dtz = kw["default_tzinfo"] = dtz
    else:
        exp_dtz = iso8601.UTC

    if fmt is not None:
        kw["format"] = fmt

    typ = DateTime(**kw)

    assert typ.default_tzinfo == exp_dtz
    assert typ.format == fmt


@pytest.mark.parametrize(
    "dtz, fmt, appstruct, exp_cstruct",
    [
        (None, None, "null", "null"),
        (None, None, None, "null"),
        (None, None, MARKER, "Invalid"),
        # non-naive datetime
        (None, None, "now_utc", "now_utc_iso"),
        (None, "%c", "now_utc", "now_utc_locale"),
        ("GMT_4", None, "now_utc", "now_utc_iso"),
        ("GMT_4", "%c", "now_utc", "now_utc_locale"),
        (None, None, "now_gmt_4", "now_gmt_4_iso"),
        (None, "%c", "now_gmt_4", "now_gmt_4_locale"),
        ("GMT_4", None, "now_gmt_4", "now_gmt_4_iso"),
        ("GMT_4", "%c", "now_gmt_4", "now_gmt_4_locale"),
        # naive datetime
        (None, None, "now_naive", "now_utc_iso"),
        (None, "%c", "now_naive", "now_utc_locale"),
        ("GMT_4", None, "now_naive", "now_gmt_4_iso"),
        ("GMT_4", "%c", "now_naive", "now_gmt_4_locale"),
        # date
        (None, None, "today", "today_mdn_utc_iso"),
        (None, "%c", "today", "today_mdn_utc_locale"),
        ("GMT_4", None, "today", "today_mdn_gmt_4_iso"),
        ("GMT_4", "%c", "today", "today_mdn_gmt_4_locale"),
    ],
)
def test_DateTime_serialize(dtz, fmt, appstruct, exp_cstruct):
    import datetime
    import iso8601

    from colander import DateTime
    from colander import Invalid
    from colander import null

    GMT_4 = iso8601.FixedOffset(-4, 0, "GMT-4")

    today = datetime.date.today()
    midnight_utc = datetime.time(0, 0, 0, 0, tzinfo=datetime.timezone.utc)
    midnight_gmt_4 = datetime.time(0, 0, 0, 0, tzinfo=GMT_4)
    today_mdn_utc = datetime.datetime.combine(today, midnight_utc)
    today_mdn_gmt_4 = datetime.datetime.combine(today, midnight_gmt_4)

    now_naive = datetime.datetime.now()
    now_utc = now_naive.replace(tzinfo=datetime.timezone.utc)
    now_gmt_4 = now_naive.replace(tzinfo=GMT_4)

    if appstruct == "null":
        appstruct = null
    elif appstruct == "now_utc":
        appstruct = now_utc
    elif appstruct == "now_gmt_4":
        appstruct = now_gmt_4
    elif appstruct == "now_naive":
        appstruct = now_naive
    elif appstruct == "today":
        appstruct = today

    if exp_cstruct == "null":
        exp_cstruct = null
    elif exp_cstruct == "now_utc_iso":
        exp_cstruct = now_utc.isoformat()
    elif exp_cstruct == "now_utc_locale":
        exp_cstruct = now_utc.strftime("%c")
    elif exp_cstruct == "now_gmt_4_iso":
        exp_cstruct = now_gmt_4.isoformat()
    elif exp_cstruct == "now_gmt_4_locale":
        exp_cstruct = now_gmt_4.strftime("%c")
    elif exp_cstruct == "today_mdn_utc_iso":
        exp_cstruct = today_mdn_utc.isoformat()
    elif exp_cstruct == "today_mdn_utc_locale":
        exp_cstruct = today_mdn_utc.strftime("%c")
    elif exp_cstruct == "today_mdn_gmt_4_iso":
        exp_cstruct = today_mdn_gmt_4.isoformat()
    elif exp_cstruct == "today_mdn_gmt_4_locale":
        exp_cstruct = today_mdn_gmt_4.strftime("%c")

    kw = {}

    if dtz == "GMT_4":
        dtz = GMT_4

    if dtz is not None:
        kw["default_tzinfo"] = dtz

    if fmt is not None:
        kw["format"] = fmt

    typ = DateTime(**kw)
    node = mock.Mock(set_spec=())

    if exp_cstruct == "Invalid":

        with pytest.raises(Invalid) as exc:
            typ.serialize(node, appstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == '"${val}" is not a datetime object'
        assert invalid.msg.mapping["val"] is appstruct

    else:
        result = typ.serialize(node, appstruct)
        assert result == exp_cstruct


@pytest.mark.parametrize(
    "dtz, fmt, cstruct, exp_appstruct",
    [
        (None, None, "null", "null"),
        (None, None, None, "null"),
        (None, None, MARKER, "Invalid"),
        # non-naive datetime
        (None, None, "now_utc_iso", "now_utc"),
        (None, "%c %z", "now_utc_locale", "now_utc_no_usecs"),
        ("GMT_4", None, "now_utc_iso", "now_utc"),
        ("GMT_4", "%c %z", "now_utc_locale", "now_utc_no_usecs"),
        # naive datetime
        (None, None, "now_naive_iso", "now_utc"),
        (None, "%c", "now_naive_locale", "now_utc_no_usecs"),
        ("GMT_4", None, "now_naive_iso", "now_gmt_4"),
        ("GMT_4", "%c", "now_naive_locale", "now_gmt_4_no_usecs"),
    ],
)
def test_DateTime_deserialize(dtz, fmt, cstruct, exp_appstruct):
    import datetime
    import iso8601

    from colander import DateTime
    from colander import Invalid
    from colander import null

    GMT_4 = iso8601.FixedOffset(-4, 0, "GMT-4")

    now_naive = datetime.datetime.now()
    now_utc = now_naive.replace(tzinfo=datetime.timezone.utc)
    now_gmt_4 = now_naive.replace(tzinfo=GMT_4)

    if cstruct == "null":
        cstruct = null
    elif cstruct == "now_naive_iso":
        cstruct = now_naive.isoformat()
    elif cstruct == "now_naive_locale":
        cstruct = now_naive.strftime("%c")
    elif cstruct == "now_utc_iso":
        cstruct = now_utc.isoformat()
    elif cstruct == "now_utc_locale":
        cstruct = now_utc.strftime("%c %z")
    elif cstruct == "now_gmt_4_iso":
        cstruct = now_gmt_4.isoformat()
    elif cstruct == "now_gmt_4_locale":
        cstruct = now_gmt_4.strftime("%c")

    if exp_appstruct == "null":
        exp_appstruct = null
    elif exp_appstruct == "now_utc":
        exp_appstruct = now_utc
    elif exp_appstruct == "now_utc_no_usecs":
        exp_appstruct = now_utc.replace(microsecond=0)
    elif exp_appstruct == "now_gmt_4":
        exp_appstruct = now_gmt_4
    elif exp_appstruct == "now_gmt_4_no_usecs":
        exp_appstruct = now_gmt_4.replace(microsecond=0)

    kw = {}

    if dtz == "GMT_4":
        dtz = GMT_4

    if dtz is not None:
        kw["default_tzinfo"] = dtz

    if fmt is not None:
        kw["format"] = fmt

    typ = DateTime(**kw)
    node = mock.Mock(set_spec=())

    if exp_appstruct == "Invalid":

        with pytest.raises(Invalid) as exc:
            typ.deserialize(node, cstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == DateTime.err_template
        assert invalid.msg.mapping["val"] is cstruct

    else:
        result = typ.deserialize(node, cstruct)
        assert result == exp_appstruct


@pytest.mark.parametrize("fmt", [None, "%c"])
def test_Date_ctor(fmt):
    from colander import Date

    kw = {}

    if fmt is not None:
        kw["format"] = fmt

    typ = Date(**kw)

    assert typ.format == fmt


@pytest.mark.parametrize(
    "fmt, appstruct, exp_cstruct",
    [
        (None, "null", "null"),
        (None, None, "null"),
        (None, MARKER, "Invalid"),
        (None, "today", "today_iso"),
        (None, "now", "today_iso"),
        ("%c", "today", "today_locale"),
        ("%c", "now", "today_locale"),
    ],
)
def test_Date_serialize(fmt, appstruct, exp_cstruct):
    import datetime

    from colander import Date
    from colander import Invalid
    from colander import null

    today = datetime.date.today()
    now = datetime.datetime.now()

    kw = {}

    if fmt is not None:
        kw["format"] = fmt

    typ = Date(**kw)
    node = mock.Mock(set_spec=())

    if appstruct == "null":
        appstruct = null
    elif appstruct == "today":
        appstruct = today
    elif appstruct == "now":
        appstruct = now

    if exp_cstruct == "null":
        exp_cstruct = null
    elif exp_cstruct == "today_iso":
        exp_cstruct = today.isoformat()
    elif exp_cstruct == "today_locale":
        exp_cstruct = today.strftime("%c")

    if exp_cstruct == "Invalid":

        with pytest.raises(Invalid) as exc:
            typ.serialize(node, appstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == '"${val}" is not a date object'
        assert invalid.msg.mapping["val"] is appstruct

    else:
        result = typ.serialize(node, appstruct)
        assert result == exp_cstruct


@pytest.mark.parametrize(
    "fmt, cstruct, exp_appstruct",
    [
        (None, "null", "null"),
        (None, None, "null"),
        (None, MARKER, "Invalid"),
        (None, "today_iso", "today"),
        ("%c", "today_locale", "today"),
    ],
)
def test_Date_deserialize(fmt, cstruct, exp_appstruct):
    import datetime

    from colander import Date
    from colander import Invalid
    from colander import null

    today = datetime.date.today()

    kw = {}

    if fmt is not None:
        kw["format"] = fmt

    typ = Date(**kw)
    node = mock.Mock(set_spec=())

    if cstruct == "null":
        cstruct = null
    elif cstruct == "today_iso":
        cstruct = today.isoformat()
    elif cstruct == "today_locale":
        cstruct = today.strftime("%c")

    if exp_appstruct == "null":
        exp_appstruct = null
    elif exp_appstruct == "today":
        exp_appstruct = today

    if exp_appstruct == "Invalid":

        with pytest.raises(Invalid) as exc:
            typ.deserialize(node, cstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == Date.err_template
        assert invalid.msg.mapping["val"] is cstruct

    else:
        result = typ.deserialize(node, cstruct)
        assert result == exp_appstruct


@pytest.mark.parametrize(
    "appstruct, exp_cstruct",
    [
        ("null", "null"),
        (None, "null"),
        (MARKER, "Invalid"),
        ("now", "now_time_iso"),
        ("now_time", "now_time_iso"),
    ],
)
def test_Time_serialize(appstruct, exp_cstruct):
    import datetime

    from colander import Invalid
    from colander import Time
    from colander import null

    now = datetime.datetime.now()
    now_time = now.time()

    typ = Time()
    node = mock.Mock(set_spec=())

    if appstruct == "null":
        appstruct = null
    elif appstruct == "now":
        appstruct = now
    elif appstruct == "now_time":
        appstruct = now_time

    if exp_cstruct == "null":
        exp_cstruct = null
    elif exp_cstruct == "now_time_iso":
        exp_cstruct = now_time.isoformat()

    if exp_cstruct == "Invalid":

        with pytest.raises(Invalid) as exc:
            typ.serialize(node, appstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == '"${val}" is not a time object'
        assert invalid.msg.mapping["val"] is appstruct

    else:
        result = typ.serialize(node, appstruct)
        assert result == exp_cstruct


@pytest.mark.parametrize(
    "fmt, cstruct, exp_appstruct",
    [
        (None, "null", "null"),
        (None, None, "null"),
        (None, MARKER, "Invalid"),
        (None, "now_iso", "now_time"),
        (None, "now_time_iso", "now_time"),
        (None, "now_time_hhmmss_f", "now_time"),
        (None, "now_time_hhmmss", "now_time_no_usecs"),
        (None, "now_time_hhmm", "now_time_no_secs"),
    ],
)
def test_Time_deserialize(fmt, cstruct, exp_appstruct):
    import datetime

    from colander import Invalid
    from colander import Time
    from colander import null

    now = datetime.datetime.now()
    now_time = now.time()

    kw = {}

    if fmt is not None:
        kw["format"] = fmt

    typ = Time(**kw)
    node = mock.Mock(set_spec=())

    if cstruct == "null":
        cstruct = null
    elif cstruct == "now_iso":
        cstruct = now.isoformat()
    elif cstruct == "now_time_iso":
        cstruct = now_time.isoformat()
    elif cstruct == "now_time_hhmmss_f":
        cstruct = now_time.strftime('%H:%M:%S.%f')
    elif cstruct == "now_time_hhmmss":
        cstruct = now_time.strftime('%H:%M:%S')
    elif cstruct == "now_time_hhmm":
        cstruct = now_time.strftime('%H:%M')

    if exp_appstruct == "null":
        exp_appstruct = null
    elif exp_appstruct == "now_time":
        exp_appstruct = now_time
    elif exp_appstruct == "now_time_no_usecs":
        exp_appstruct = now_time.replace(microsecond=0)
    elif exp_appstruct == "now_time_no_secs":
        exp_appstruct = now_time.replace(second=0, microsecond=0)

    if exp_appstruct == "Invalid":

        with pytest.raises(Invalid) as exc:
            typ.deserialize(node, cstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == Time.err_template
        assert invalid.msg.mapping["val"] is cstruct

    else:
        result = typ.deserialize(node, cstruct)
        assert result == exp_appstruct


@pytest.fixture(scope="module")
def test_enum():
    import enum

    class TestEnum(enum.Enum):
        FOO = 1
        BAR = 2
        BAZ = 3

        @property
        def valstr(self):
            return str(self.value)

    return TestEnum


@pytest.mark.parametrize(
    "attr, exp_attr",
    [
        (None, "name"),
        ("name", "name"),
        ("valstr", "valstr"),
        ("bogus", "AttributeError"),
        ("FOO", "ValueError"),
    ],
)
@pytest.mark.parametrize(
    "val_typ, exp_typ",
    [
        (None, "string"),
        ("integer", "integer"),
    ],
)
def test_Enum_ctor(test_enum, attr, exp_attr, val_typ, exp_typ):
    from colander import Enum
    from colander import Integer
    from colander import String

    kw = {}

    if attr is not None:
        kw["attr"] = attr

    if val_typ == "integer":
        val_typ = Integer

    if exp_typ == "string":
        exp_typ = String
    elif exp_typ == "integer":
        exp_typ = Integer

    if val_typ is not None:
        kw["typ"] = val_typ()

    if exp_attr == "AttributeError":

        with pytest.raises(AttributeError):
            Enum(test_enum, **kw)

    elif exp_attr == "ValueError":

        with pytest.raises(ValueError):
            Enum(test_enum, **kw)

    else:

        typ = Enum(test_enum, **kw)

        assert typ.enum_cls is test_enum
        assert typ.attr == exp_attr
        assert isinstance(typ.typ, exp_typ)

        if exp_attr == "name":
            assert typ.values == test_enum.__members__

        elif exp_attr == "valstr":
            assert typ.values["1"] == test_enum.FOO
            assert typ.values["2"] == test_enum.BAR
            assert typ.values["3"] == test_enum.BAZ


@pytest.mark.parametrize(
    "attr, val_typ, appstruct, exp_cstruct",
    [
        ("name", "string", "null", "null"),
        ("name", "string", MARKER, "Invalid"),
        ("name", "string", "FOO", "FOO"),
        ("value", "integer", "FOO", "1"),
        ("valstr", "string", "BAR", "2"),
    ],
)
def test_Enum_serialize(test_enum, attr, val_typ, appstruct, exp_cstruct):
    from colander import Enum
    from colander import Integer
    from colander import Invalid
    from colander import String
    from colander import null

    if val_typ == "integer":
        val_typ = Integer
    elif val_typ == "string":
        val_typ = String

    if appstruct == "null":
        appstruct = null
    elif appstruct is not MARKER:
        appstruct = getattr(test_enum, appstruct)

    if exp_cstruct == "null":
        exp_cstruct = null

    typ = Enum(test_enum, attr=attr, typ=val_typ())
    node = mock.Mock(set_spec=())

    if exp_cstruct == "Invalid":

        with pytest.raises(Invalid) as exc:
            typ.serialize(node, appstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == '"${val}" is not a valid "${cls}"'
        assert invalid.msg.mapping["val"] is appstruct
        assert invalid.msg.mapping["cls"] == test_enum.__name__
    else:
        result = typ.serialize(node, appstruct)
        assert result == exp_cstruct


@pytest.mark.parametrize(
    "attr, val_typ, cstruct, exp_appstruct",
    [
        ("name", "string", "null", "null"),
        ("name", "string", MARKER, "InvalidType"),
        ("name", "string", "QUX", "InvalidValue"),
        ("name", "string", "FOO", "FOO"),
        ("value", "integer", 1, "FOO"),
        ("valstr", "string", "2", "BAR"),
    ],
)
def test_Enum_deserialize(test_enum, attr, val_typ, cstruct, exp_appstruct):
    from colander import Enum
    from colander import Integer
    from colander import Invalid
    from colander import String
    from colander import null

    if val_typ == "integer":
        val_typ = Integer
    elif val_typ == "string":
        val_typ = String

    if cstruct == "null":
        cstruct = null

    if exp_appstruct == "null":
        exp_appstruct = null
    elif not exp_appstruct.startswith("Invalid"):
        exp_appstruct = getattr(test_enum, exp_appstruct)

    typ = Enum(test_enum, attr=attr, typ=val_typ())
    node = mock.Mock(set_spec=())

    if exp_appstruct in ("InvalidType", "InvalidValue"):

        with pytest.raises(Invalid) as exc:
            typ.deserialize(node, cstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)

        if exp_appstruct == "InvalidType":
            assert invalid.msg.default == '${val} is not a string: ${err}'
            assert invalid.msg.mapping["val"] is cstruct
        elif exp_appstruct == "InvalidValue":
            assert invalid.msg.default == '"${val}" is not a valid "${cls}"'
            assert invalid.msg.mapping["val"] is cstruct
            assert invalid.msg.mapping["cls"] == test_enum.__name__
    else:
        result = typ.deserialize(node, cstruct)
        assert result == exp_appstruct
