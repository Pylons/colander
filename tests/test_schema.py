from unittest import mock

import pytest
import translationstring

MARKER = object()


@pytest.mark.parametrize(
    "before, exists, exp_set, exp_add, exp_del, exp_before",
    [
        (None, False, False, True, False, False),
        (None, True, True, False, False, False),
        ("test_before", False, False, False, False, True),
        ("test_before", True, False, False, True, True),
    ],
)
def test__add_node_child(
    before,
    exists,
    exp_set,
    exp_add,
    exp_del,
    exp_before,
):
    from colander import _add_node_child

    CHILD_NAME = "child"

    class Node(dict):
        _added = None
        _added_before = None

        def add(self, child):
            self._added = child

        def add_before(self, insert_before, child):
            self._added_before = (insert_before, child)

    node = Node()
    child = mock.Mock()
    child.name = CHILD_NAME

    child.insert_before = before

    if exists:
        node[CHILD_NAME] = object()

    _add_node_child(node, child)

    if exp_set:
        assert node[CHILD_NAME] is child

    if exp_add:
        assert node._added is child

    if exp_del:
        assert CHILD_NAME not in node

    if exp_before:
        assert node._added_before == (before, child)


@pytest.mark.parametrize("child_names", [[], ["a"], ["a", "b"]])
def test__add_node_children(child_names):
    from colander import _add_node_children

    node = mock.Mock(spec_set=())
    children = [mock.Mock(name=name) for name in child_names]

    with mock.patch("colander._add_node_child") as anc:
        _add_node_children(node, children)

    if len(children) > 0:
        assert len(anc.call_args_list) == len(children)

        for i_child, child in enumerate(children):
            called = anc.call_args_list[i_child]
            assert called.args == (node, child)

    else:
        anc.assert_not_called()


def test_SchemaNode_new_sets_order():
    from colander import SchemaNode

    # Contorted because 'itertools.counter' has no other way to peek
    _, (before,) = SchemaNode._counter.__reduce__()

    node = SchemaNode(None)

    _, (after,) = SchemaNode._counter.__reduce__()
    assert node._order == before
    assert after == before + 1


@pytest.mark.parametrize(
    "arg, kw, exp_typ",
    [
        ((), {}, "NotImplementedError"),
        ((), {"typ": "Integer"}, "Integer"),
        (("Integer",), {}, "Integer"),
    ],
)
def test_SchemaNode_ctor_typ(arg, kw, exp_typ):
    from colander import Integer
    from colander import SchemaNode

    if exp_typ == "Integer":
        exp_typ = Integer

    if arg and arg[0] == "Integer":
        arg = (Integer,) + arg[1:]

    if kw.get("typ") == "Integer":
        kw["typ"] = Integer

    if exp_typ == "NotImplementedError":
        with pytest.raises(NotImplementedError):
            SchemaNode(*arg, **kw)
    else:
        node = SchemaNode(*arg, **kw)

        assert node.typ is Integer
        assert node.children == []


def test_SchemaNode_ctor_children():
    from colander import SchemaNode

    children = [SchemaNode(None, name=f"child_{i}") for i in range(10)]

    with mock.patch("colander._add_node_children") as anc:
        node = SchemaNode(None, *children)

    assert len(anc.call_args_list) == 2
    assert anc.call_args_list[0].args == (node, [])  # __new__
    assert anc.call_args_list[1].args == (node, tuple(children))  # __init__


@pytest.mark.parametrize(
    "kw, exp_title, raw_set",
    [
        ({}, "", False),
        ({"title": "Foo"}, "Foo", True),
        ({"name": "node_name"}, "Node Name", False),
    ],
)
def test_SchemaNode_ctor_title(kw, exp_title, raw_set):
    from colander import SchemaNode
    from colander import required

    node = SchemaNode(None, **kw)

    assert node.title == exp_title

    if raw_set:
        assert node.raw_title == exp_title
    else:
        assert node.raw_title is required


@pytest.mark.parametrize(
    "kw",
    [
        {"preparer": 1},
        {"validator": 1},
        {"default": 1},
        {"missing": 1},
        {"missing_msg": "msg"},
        {"name": "name"},
        {"description": "description"},
        {"widget": 1},
        {"after_bind": 1},
        {"bindings": 1},
        {
            "preparer": 1,
            "validator": 1,
            "default": 1,
            "missing": 1,
            "missing_msg": "msg",
            "name": "name",
            "description": "description",
            "widget": 1,
            "after_bind": 1,
            "bindings": 1,
        },
        {"foo": 1},
    ],
)
def test_SchemaNode_ctor_other_kw(kw):
    from colander import SchemaNode

    node = SchemaNode(None, **kw)

    for key, value in kw.items():
        assert getattr(node, key) == value


def _later():
    pass


@pytest.mark.parametrize(
    "missing, expected",
    [(None, True), ("deferred", True), (1, False)],
)
def test_SchemaNode_required(missing, expected):
    from colander import SchemaNode
    from colander import deferred

    if missing == "deferred":
        missing = deferred(_later)

    if missing is None:
        node = SchemaNode(None)
    else:
        node = SchemaNode(None, missing=missing)

    assert node.required == expected


@pytest.mark.parametrize(
    "appstruct, exp_cstruct",
    [(None, "14"), ("null", "14"), ("deferred", "null"), (1, "1")],
)
def test_SchemaNode_serialize(appstruct, exp_cstruct):
    from colander import Integer
    from colander import SchemaNode
    from colander import deferred
    from colander import null

    node = SchemaNode(Integer(), default=14)

    if appstruct == "null":
        appstruct = null
    elif appstruct == "deferred":
        appstruct = deferred(_later)

    if exp_cstruct == "null":
        exp_cstruct = null

    if appstruct is None:
        result = node.serialize()
    else:
        result = node.serialize(appstruct)

    assert result == exp_cstruct


def test_SchemaNode_flatten():
    from colander import SchemaNode

    typ = mock.Mock(spec_set=["flatten"])
    node = SchemaNode(typ)
    appstruct = {"foo": "Foo"}

    result = node.flatten(appstruct)

    assert result is typ.flatten.return_value
    typ.flatten.assert_called_once_with(node, appstruct)


def test_SchemaNode_unflatten():
    from colander import SchemaNode

    typ = mock.Mock(spec_set=["unflatten"])
    node = SchemaNode(typ)
    fstruct = {"foo": "Foo", "bar": "Bar"}

    result = node.unflatten(fstruct)

    assert result is typ.unflatten.return_value
    typ.unflatten.assert_called_once_with(node, sorted(fstruct), fstruct)


def test_SchemaNode_set_value():
    from colander import SchemaNode

    typ = mock.Mock(spec_set=["set_value"])
    node = SchemaNode(typ)
    appstruct = {"foo": "Foo", "bar": "Bar"}

    node.set_value(appstruct, "foo", "New Foo")

    typ.set_value.assert_called_once_with(node, appstruct, "foo", "New Foo")


def test_SchemaNode_get_value():
    from colander import SchemaNode

    typ = mock.Mock(spec_set=["get_value"])
    node = SchemaNode(typ)
    appstruct = {"foo": "Foo", "bar": "Bar"}

    result = node.get_value(appstruct, "foo")

    assert result is typ.get_value.return_value
    typ.get_value.assert_called_once_with(node, appstruct, "foo")


@pytest.mark.parametrize(
    "missing, cstruct, exp_appstruct",
    [
        (None, "1", 1),
        (14, None, 14),
        (14, "null", 14),
        (None, "null", "Invalid"),
        (None, None, "Invalid"),
        ("deferred", "null", "Invalid"),
        ("deferred", None, "Invalid"),
        ("null", "null", "null"),
    ],
)
def test_SchemaNode_deserialize_wo_preparer_wo_validator(
    missing, cstruct, exp_appstruct
):
    from colander import Integer
    from colander import Invalid
    from colander import SchemaNode
    from colander import deferred
    from colander import null

    if missing == "null":
        missing = null
    elif missing == "deferred":
        missing = deferred(_later)

    if missing is None:
        node = SchemaNode(Integer(), name="must")
    else:
        node = SchemaNode(Integer(), missing=missing)

    if cstruct == "null":
        cstruct = null

    if exp_appstruct == "null":
        exp_appstruct = null

    if exp_appstruct == "Invalid":

        with pytest.raises(Invalid) as exc:
            if cstruct is None:
                node.deserialize()
            else:
                node.deserialize(cstruct)

        invalid = exc.value
        assert invalid.node is node
        assert isinstance(invalid.msg, translationstring.TranslationString)
        assert invalid.msg.default == node.missing_msg

        if missing is None:
            assert invalid.msg.mapping["title"] == node.title
            assert invalid.msg.mapping["name"] == node.name
        else:
            assert invalid.msg.mapping is None

    else:
        if cstruct is None:
            result = node.deserialize()
        else:
            result = node.deserialize(cstruct)

        assert result == exp_appstruct


def test_SchemaNode_deserialize_w_preparer():
    from colander import Integer
    from colander import SchemaNode

    cstruct = "1"
    preparer = mock.Mock(spec_set=(), return_value=23)
    node = SchemaNode(Integer(), preparer=preparer)

    result = node.deserialize(cstruct)

    assert result == 23
    preparer.assert_called_once_with(1)


def test_SchemaNode_deserialize_w_preparers():
    from colander import Integer
    from colander import SchemaNode

    cstruct = "1"
    prep_1 = mock.Mock(spec_set=(), return_value=45)
    prep_2 = mock.Mock(spec_set=(), return_value=67)
    prep_3 = mock.Mock(spec_set=(), return_value=89)
    node = SchemaNode(Integer(), preparer=[prep_1, prep_2, prep_3])

    result = node.deserialize(cstruct)

    assert result == 89
    prep_1.assert_called_once_with(1)
    prep_2.assert_called_once_with(45)
    prep_3.assert_called_once_with(67)


def test_SchemaNode_deserialize_w_validator_deferred():
    from colander import Integer
    from colander import SchemaNode
    from colander import UnboundDeferredError
    from colander import deferred

    cstruct = "1"
    validator = deferred(_later)
    node = SchemaNode(Integer(), validator=validator)

    with pytest.raises(UnboundDeferredError):
        node.deserialize(cstruct)


def test_SchemaNode_deserialize_w_validator_raises():
    from colander import Integer
    from colander import SchemaNode

    cstruct = "1"
    validator = mock.Mock(spec_set=(), side_effect=ValueError("testing"))
    node = SchemaNode(Integer(), validator=validator)

    with pytest.raises(ValueError):
        node.deserialize(cstruct)

    validator.assert_called_once_with(node, 1)


def test_SchemaNode_deserialize_w_validator_no_raise():
    from colander import Integer
    from colander import SchemaNode

    cstruct = "1"
    validator = mock.Mock(spec_set=())
    node = SchemaNode(Integer(), validator=validator)

    result = node.deserialize(cstruct)

    assert result == 1
    validator.assert_called_once_with(node, 1)


def test_SchemaNode_add():
    from colander import SchemaNode

    pre_1 = SchemaNode(None, name="pre_1")
    pre_2 = SchemaNode(None, name="pre_2")
    child = SchemaNode(None, name="child")
    node = SchemaNode(None, pre_1, pre_2)

    node.add(child)

    assert node.children == [pre_1, pre_2, child]


def test_SchemaNode_insert():
    from colander import SchemaNode

    pre_1 = SchemaNode(None, name="pre_1")
    pre_2 = SchemaNode(None, name="pre_2")
    child = SchemaNode(None, name="child")
    node = SchemaNode(None, pre_1, pre_2)

    node.insert(1, child)

    assert node.children == [pre_1, child, pre_2]


def test_SchemaNode_add_before_miss():
    from colander import SchemaNode

    child = SchemaNode(None, name="child")
    node = SchemaNode(None)

    with pytest.raises(KeyError):
        node.add_before("pre_2", child)


def test_SchemaNode_add_before_hit():
    from colander import SchemaNode

    pre_1 = SchemaNode(None, name="pre_1")
    pre_2 = SchemaNode(None, name="pre_2")
    child = SchemaNode(None, name="child")
    node = SchemaNode(None, pre_1, pre_2)

    node.add_before("pre_2", child)

    assert node.children == [pre_1, child, pre_2]


@pytest.mark.parametrize(
    "name, default, expected",
    [
        ("c_1", None, "c_1"),
        ("c_2", MARKER, "c_2"),
        ("nonesuch", None, None),
        ("nonesuch", MARKER, MARKER),
    ],
)
def test_SchemaNode_get(name, default, expected):
    from colander import SchemaNode

    c_1 = SchemaNode(None, name="c_1")
    c_2 = SchemaNode(None, name="c_2")
    node = SchemaNode(None, c_1, c_2)

    if expected == "c_1":
        expected = c_1
    elif expected == "c_2":
        expected = c_2

    if default is None:
        result = node.get(name)
    else:
        result = node.get(name, default)

    assert result == expected


@pytest.mark.parametrize(
    "kw",
    [
        {"preparer": 1},
        {"validator": 1},
        {"default": 1},
        {"missing": 1},
        {"missing_msg": "msg"},
        {"name": "name"},
        {"description": "description"},
        {"widget": 1},
        {"after_bind": 1},
        {"bindings": 1},
        {
            "preparer": 1,
            "validator": 1,
            "default": 1,
            "missing": 1,
            "missing_msg": "msg",
            "name": "name",
            "description": "description",
            "widget": 1,
            "after_bind": 1,
            "bindings": 1,
        },
        {"foo": 1},
    ],
)
def test_SchemaNode_clone_wo_children(kw):
    from colander import Integer
    from colander import SchemaNode

    typ = Integer()
    node = SchemaNode(typ, **kw)

    cloned = node.clone()

    assert cloned is not node
    assert cloned.typ is typ

    for key, value in kw.items():
        assert getattr(cloned, key) == value


def test_SchemaNode_clone_w_children():
    from colander import Integer
    from colander import SchemaNode

    c_typ = Integer()
    c_1 = SchemaNode(c_typ, name="c_1")
    c_2 = SchemaNode(c_typ, name="c_2")
    c_3 = SchemaNode(c_typ, name="c_3")
    node = SchemaNode(None, c_1, c_2, c_3)

    cloned = node.clone()

    assert cloned is not node
    assert cloned.typ is None

    assert len(cloned.children) == len(node.children)
    for c_cloned, c_pre in zip(cloned.children, node.children):
        assert c_cloned is not c_pre
        assert c_cloned.name == c_pre.name


@pytest.mark.parametrize(
    "ctor_kw, after_bind",
    [
        ({"missing": "deferred"}, False),
        ({"default": "deferred"}, False),
        ({"validator": "deferred"}, False),
        (
            {"missing": 1, "default": 2, "validator": 3, "foo": "deferred"},
            True,
        ),
    ],
)
def test_SchemaNode_bind_wo_children(ctor_kw, after_bind):
    from colander import Integer
    from colander import SchemaNode
    from colander import deferred

    deferreds = {}

    for key, value in list(ctor_kw.items()):
        if value == "deferred":
            deferreds[key] = func = mock.Mock(name=key, spec_set=())
            ctor_kw[key] = deferred(func)

    if after_bind:
        ctor_kw["after_bind"] = mock.Mock(spec_sec=())

    typ = Integer()
    node = SchemaNode(typ, **ctor_kw)
    bind_kw = {"bar": "Bar"}

    bound = node.bind(**bind_kw)

    assert bound is not node
    assert bound.typ is typ
    assert bound.bindings == bind_kw

    for key in ctor_kw:
        value = getattr(bound, key)

        if key in deferreds:
            func = deferreds[key]
            assert value is func.return_value
            func.assert_called_once_with(bound, bind_kw)
        else:
            assert getattr(bound, key) == value

    if after_bind:
        ctor_kw["after_bind"].assert_called_once_with(bound, bind_kw)


def test_SchemaNode_bind_w_children():
    from colander import Integer
    from colander import SchemaNode

    after_bound = []

    def after_bind(node, kw):
        after_bound.append((node, kw))

    c_typ = Integer()
    c_1 = SchemaNode(c_typ, name="c_1", after_bind=after_bind)
    c_2 = SchemaNode(c_typ, name="c_2", after_bind=after_bind)
    c_3 = SchemaNode(c_typ, name="c_3", after_bind=after_bind)
    node = SchemaNode(None, c_1, c_2, c_3, after_bind=after_bind)
    bind_kw = {"bar": "Bar"}

    bound = node.bind(**bind_kw)
    assert after_bound[-1] == (bound, bind_kw)

    assert len(after_bound) == len(node.children) + 1
    assert len(bound.children) == len(node.children)

    for i_c, (c_bound, c_pre) in enumerate(zip(bound.children, node.children)):
        assert c_bound is not c_pre
        assert c_bound.name == c_pre.name
        assert after_bound[i_c] == (c_bound, bind_kw)


@pytest.mark.parametrize("has_name", [False, True])
@pytest.mark.parametrize("has_title", [False, True])
def test_SchemaNode_bind_w_deferred_returning_child(has_name, has_title):
    from colander import Integer
    from colander import SchemaNode
    from colander import deferred

    def _make_child_node(node, kw):
        return SchemaNode(Integer(), **kw)

    typ = Integer()
    node = SchemaNode(typ, child=deferred(_make_child_node))
    assert len(node.children) == 0

    bind_kw = {}

    if has_name:
        bind_kw["name"] = "child_name"

    if has_title:
        bind_kw["title"] = "Child Title"

    bound = node.bind(**bind_kw)

    assert len(bound.children) == 1
    child = bound.children[0]

    if has_name:
        assert child.name == "child_name"
    else:
        assert child.name == "child"

    if has_title:
        assert child.title == "Child Title"
    else:
        assert child.title == "Child"


def test_SchemaNode_cstruct_children_typ_wo_c_c():
    import warnings

    from colander import SchemaNode

    node = SchemaNode(None)
    cstruct = {}

    with warnings.catch_warnings(record=True) as warned:
        result = node.cstruct_children(cstruct)

    assert result == []
    assert len(warned) == 1
    warning = warned[0]
    assert warning.category is DeprecationWarning


def test_SchemaNode_cstruct_children_hit():
    from colander import SchemaNode

    typ = mock.Mock(spec_set=["cstruct_children"])
    node = SchemaNode(typ=typ)
    cstruct = {}

    result = node.cstruct_children(cstruct)

    assert result is typ.cstruct_children.return_value
    typ.cstruct_children.assert_called_once_with(node, cstruct)


def test_SchemaNode___delitem___miss():
    from colander import SchemaNode

    node = SchemaNode(None)

    with pytest.raises(KeyError):
        del node["nonesuch"]


def test_SchemaNode___delitem___hit():
    from colander import SchemaNode

    node = SchemaNode(None)
    child = SchemaNode(None, name="child_name")
    node.add(child)

    del node["child_name"]
    assert len(node.children) == 0


def test_SchemaNode___getitem___miss():
    from colander import SchemaNode

    node = SchemaNode(None)

    with pytest.raises(KeyError):
        node["nonesuch"]


def test_SchemaNode___getitem___hit():
    from colander import SchemaNode

    node = SchemaNode(None)
    child = SchemaNode(None, name="child_name")
    node.add(child)

    result = node["child_name"]

    assert result is child


def test_SchemaNode___setitem___new():
    from colander import SchemaNode

    node = SchemaNode(None)
    child = SchemaNode(None)

    node["child_name"] = child

    assert len(node.children) == 1
    assert child.name == "child_name"


def test_SchemaNode___setitem___replacement():
    from colander import SchemaNode

    node = SchemaNode(None)
    before = SchemaNode(None, name="child_name")
    node.add(before)
    after = SchemaNode(None)

    node["child_name"] = after

    assert len(node.children) == 1
    assert node.children[0] is after
    assert after.name == "child_name"


def test_SchemaNode___iter___empty():
    from colander import SchemaNode

    node = SchemaNode(None)

    result = list(node)

    assert result == []


def test_SchemaNode___iter___nonempty():
    from colander import SchemaNode

    c_1 = SchemaNode(None, name="child_1")
    c_2 = SchemaNode(None, name="child_2")
    c_3 = SchemaNode(None, name="child_3")
    node = SchemaNode(None, c_1, c_2, c_3)

    result = list(node)

    assert result == [c_1, c_2, c_3]


def test_SchemaNode___contains___miss():
    from colander import SchemaNode

    node = SchemaNode(None)

    result = "nonesuch" in node

    assert not result


def test_SchemaNode___contains___hit():
    from colander import SchemaNode

    child = SchemaNode(None, name="child_name")
    node = SchemaNode(None, child)

    result = "child_name" in node

    assert result


def test_SchemaNode__raise_invalid_wo_node():
    from colander import Invalid
    from colander import SchemaNode

    node = SchemaNode(None)

    with pytest.raises(Invalid) as exc:
        node.raise_invalid("testing")

    invalid = exc.value
    assert invalid.node is node
    assert invalid.msg == "testing"


def test_SchemaNode__raise_invalid_w_node():
    from colander import Invalid
    from colander import SchemaNode

    node = SchemaNode(None)
    other = SchemaNode(None)

    with pytest.raises(Invalid) as exc:
        node.raise_invalid("testing", node=other)

    invalid = exc.value
    assert invalid.node is other
    assert invalid.msg == "testing"


def test_Schema_ctor_wo_children():
    from colander import Mapping
    from colander import Schema

    schema = Schema()

    assert isinstance(schema.typ, Mapping)
    assert schema.children == []


def test_Schema_ctor_w_children():
    from colander import Mapping
    from colander import Schema
    from colander import SchemaNode

    c_1 = SchemaNode(None, name="c_1")
    c_2 = SchemaNode(None, name="c_2")

    schema = Schema(c_1, c_2)

    assert isinstance(schema.typ, Mapping)
    assert schema.children == [c_1, c_2]
    assert schema["c_1"] == c_1
    assert schema["c_2"] == c_2


def test_MappingSchema_ctor_wo_children():
    from colander import Mapping
    from colander import MappingSchema

    schema = MappingSchema()

    assert isinstance(schema.typ, Mapping)
    assert schema.children == []


def test_MappingSchema_ctor_w_children():
    from colander import Mapping
    from colander import MappingSchema
    from colander import SchemaNode

    c_1 = SchemaNode(None, name="c_1")
    c_2 = SchemaNode(None, name="c_2")

    schema = MappingSchema(c_1, c_2)

    assert isinstance(schema.typ, Mapping)
    assert schema.children == [c_1, c_2]
    assert schema["c_1"] == c_1
    assert schema["c_2"] == c_2


def test_TupleSchema_ctor_wo_children():
    from colander import Tuple
    from colander import TupleSchema

    schema = TupleSchema()

    assert isinstance(schema.typ, Tuple)
    assert schema.children == []


def test_TupleSchema_ctor_w_children():
    from colander import SchemaNode
    from colander import Tuple
    from colander import TupleSchema

    c_1 = SchemaNode(None, name="c_1")
    c_2 = SchemaNode(None, name="c_2")

    schema = TupleSchema(c_1, c_2)

    assert isinstance(schema.typ, Tuple)
    assert schema.children == [c_1, c_2]
    assert schema["c_1"] == c_1
    assert schema["c_2"] == c_2


def test_SequenceSchema_ctor_w_one_child():
    from colander import SchemaNode
    from colander import Sequence
    from colander import SequenceSchema

    c_1 = SchemaNode(None, name="c_1")

    schema = SequenceSchema(c_1)

    assert isinstance(schema.typ, Sequence)
    assert schema.children == [c_1]


def test_SequenceSchema_ctor_wo_children():
    from colander import Invalid
    from colander import SequenceSchema

    with pytest.raises(Invalid) as exc:
        SequenceSchema()

    invalid = exc.value
    assert invalid.msg == 'Sequence schemas must have exactly one child node'


def test_SequenceSchema_ctor_w_surplus_children():
    from colander import Invalid
    from colander import SchemaNode
    from colander import SequenceSchema

    c_1 = SchemaNode(None, name="c_1")
    c_2 = SchemaNode(None, name="c_2")

    with pytest.raises(Invalid) as exc:
        SequenceSchema(c_1, c_2)

    invalid = exc.value
    assert invalid.msg == 'Sequence schemas must have exactly one child node'


def test_SequenceSchema_clone():
    from colander import Integer
    from colander import SchemaNode
    from colander import SequenceSchema

    child = SchemaNode(Integer(), name="child")
    schema = SequenceSchema(child)

    cloned = schema.clone()

    assert cloned is not schema
    assert cloned.typ is schema.typ

    assert len(cloned.children) == 1
    c_cloned = cloned.children[0]
    assert c_cloned is not child
    assert c_cloned.name == child.name


def test_deferred_ctor():
    from colander import deferred

    def wrapped(node, kw):
        """Can you hear me now?"""
        pass  # pragma: no cover

    inst = deferred(wrapped)

    assert inst.wrapped is wrapped
    assert inst.__doc__ == 'Can you hear me now?'
    assert inst.__name__ == 'wrapped'


def test_deferred___call__():
    from colander import deferred

    n = object()
    k = object()

    def wrapped(node, kw):
        assert node == n
        assert kw == k
        return 'abc'

    inst = deferred(wrapped)

    result = inst(n, k)

    assert result == 'abc'


def test_deferred_w_callable_instance_no_name():
    from colander import deferred

    class Wrapped:
        """CLASS"""

        def __call__(self, node, kw):
            """METHOD"""
            pass  # pragma: no cover

    wrapped = Wrapped()
    inst = deferred(wrapped)

    assert inst.__doc__ == wrapped.__doc__

    assert '__name__' not in inst.__dict__


def test_deferred_w_callable_instance_no_name_or_doc():
    from colander import deferred

    class Wrapped:
        def __call__(self, node, kw):
            pass  # pragma: no cover

    wrapped = Wrapped()

    inst = deferred(wrapped)

    assert inst.__doc__ is None
    assert '__name__' not in inst.__dict__


def test_deferred_w_insert_before():
    from colander import Integer
    from colander import Schema
    from colander import SchemaNode
    from colander import deferred

    def wrapped_func(node, kw):
        return SchemaNode(Integer(), insert_before='name2')

    class MySchema(Schema):
        name2 = SchemaNode(Integer())
        name3 = SchemaNode(Integer())
        name1 = deferred(wrapped_func)
        name4 = SchemaNode(Integer())

    unbound = MySchema()

    unbound_names = [x.name for x in unbound.children]

    # Child not present before binding
    assert unbound_names == ['name2', 'name3', 'name4']

    bound = unbound.bind()

    bound_names = [x.name for x in bound.children]

    assert bound_names == ['name1', 'name2', 'name3', 'name4']


@pytest.mark.parametrize("args, kw", [((), {}), (("foo",), {"bar": "Bar"})])
def test_instantiate(args, kw):
    from colander import instantiate

    class_ = mock.Mock(spec_set=())

    decorator = instantiate(*args, **kw)

    result = decorator(class_)

    assert result is class_.return_value
    class_.assert_called_once_with(*args, **kw)
