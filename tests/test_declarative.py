import pytest

# SND:  SchemaNode, declarative


def test_SND_validator_method():
    from colander import Integer
    from colander import Invalid
    from colander import SchemaNode

    class MyNode(SchemaNode):
        schema_type = Integer
        name = 'my'

        def validator(self, node, cstruct):
            if cstruct > 10:
                self.raise_invalid('Wrong')

    node = MyNode()

    with pytest.raises(Invalid):
        node.deserialize(20)


def test_SND_missing():
    from colander import Integer
    from colander import SchemaNode
    from colander import null

    class MyNode(SchemaNode):
        schema_type = Integer
        name = 'my'
        missing = 10

    node = MyNode()

    result = node.deserialize(null)

    assert result == 10


def test_SND_title():
    from colander import Integer
    from colander import SchemaNode

    class MyNode(SchemaNode):
        schema_type = Integer
        title = 'some title'

    node = MyNode(name='my')

    assert node.title == 'some title'


def test_SND_title_overwritten_by_constructor():
    from colander import Integer
    from colander import SchemaNode

    class MyNode(SchemaNode):
        schema_type = Integer
        title = 'some title'

    node = MyNode(name='my', title='other title')

    assert node.title == 'other title'


def test_SND_subelement_title_not_overwritten():
    from colander import Schema
    from colander import SchemaNode
    from colander import String

    class SampleNode(SchemaNode):
        schema_type = String
        title = 'Some Title'

    class SampleSchema(Schema):
        node = SampleNode()

    schema = SampleSchema()

    assert 'Some Title' == schema.children[0].title


def test_SND_subclass_value_overridden_by_constructor():
    from colander import Integer
    from colander import SchemaNode
    from colander import null

    class MyNode(SchemaNode):
        schema_type = Integer
        name = 'my'
        missing = 10

    node = MyNode(missing=5)

    result = node.deserialize(null)

    assert result == 5


def test_SND_method_values_can_rely_on_binding():
    from colander import Integer
    from colander import SchemaNode

    class MyNode(SchemaNode):
        schema_type = Integer

        def amethod(self):
            return self.bindings['request']

    node = MyNode()

    newnode = node.bind(request=14)

    assert newnode.amethod() == 14


def test_SND_nonmethod_values_can_rely_on_after_bind():
    from colander import Integer
    from colander import SchemaNode
    from colander import null

    class MyNode(SchemaNode):
        schema_type = Integer

        def after_bind(self, node, kw):
            self.missing = kw['missing']

    node = MyNode()

    newnode = node.bind(missing=10)

    assert newnode.deserialize(null) == 10


def test_SND_deferred_methods_dont_quite_work_yet():
    from colander import Integer
    from colander import SchemaNode
    from colander import deferred

    class MyNode(SchemaNode):
        schema_type = Integer

        @deferred
        def avalidator(self, node, kw):  # pragma: no cover
            def _avalidator(node, cstruct):
                self.raise_invalid('Foo')

            return _avalidator

    node = MyNode()

    with pytest.raises(TypeError):
        node.bind()


def test_SND_nonmethod_values_can_be_deferred_though():
    from colander import Integer
    from colander import SchemaNode
    from colander import deferred
    from colander import null

    def _missing(node, kw):
        return 10

    class MyNode(SchemaNode):
        schema_type = Integer
        missing = deferred(_missing)

    node = MyNode()

    bound_node = node.bind()

    assert bound_node.deserialize(null) == 10


def test_SND_functions_can_be_deferred():
    from colander import Integer
    from colander import SchemaNode
    from colander import deferred
    from colander import null

    class MyNode(SchemaNode):
        schema_type = Integer

        @deferred
        def missing(node, kw):
            return 10

    node = MyNode()
    bound_node = node.bind()
    assert bound_node.deserialize(null) == 10


def test_SND_nodes_can_be_defered():
    from colander import MappingSchema
    from colander import SchemaNode
    from colander import String
    from colander import deferred

    class MySchema(MappingSchema):
        @deferred
        def child(node, kw):
            return SchemaNode(String(), missing='foo')

    node = MySchema()
    bound_node = node.bind()
    assert bound_node.deserialize({}) == {'child': 'foo'}


def test_SND_child_names_conflict_with_value_names_notused():
    from colander import Mapping
    from colander import SchemaNode
    from colander import String

    class MyNode(SchemaNode):
        schema_type = Mapping
        title = SchemaNode(String())

    node = MyNode()
    assert node.title == ''


def test_SND_child_names_conflict_with_value_names_used():
    from colander import Mapping
    from colander import SchemaNode
    from colander import String

    doesntmatter = SchemaNode(String(), name='name')

    class MyNode(SchemaNode):
        schema_type = Mapping
        name = 'fred'
        wontmatter = doesntmatter

    node = MyNode()
    assert node.name == 'fred'
    assert node['name'] is doesntmatter


def test_SND_child_names_conflict_with_value_names_in_superclass():
    from colander import Mapping
    from colander import SchemaNode
    from colander import String

    doesntmatter = SchemaNode(String(), name='name')
    _name = SchemaNode(String())

    class MyNode(SchemaNode):
        schema_type = Mapping
        name = 'fred'
        wontmatter = doesntmatter

    class AnotherNode(MyNode):
        name = _name

    node = AnotherNode()
    assert node.name == 'fred'
    assert node['name'] is _name


def test_SND_child_names_conflict_with_value_names_in_subclass():
    from colander import Mapping
    from colander import SchemaNode
    from colander import String

    class MyNode(SchemaNode):
        name = SchemaNode(String(), id='name')

    class AnotherNode(MyNode):
        schema_type = Mapping
        name = 'fred'
        doesntmatter = SchemaNode(String(), name='name', id='doesntmatter')

    node = AnotherNode()
    assert node.name == 'fred'
    assert node['name'].id == 'doesntmatter'


def test_SND_name_reassignment():
    # see https://github.com/Pylons/colander/issues/39
    from colander import Integer
    from colander import Schema
    from colander import SchemaNode
    from colander import Sequence

    class FnordSchema(Schema):
        fnord = SchemaNode(
            Sequence(),
            SchemaNode(Integer(), name=''),
            name="fnord[]",
        )

    schema = FnordSchema()

    assert schema['fnord[]'].name == 'fnord[]'


# MSI:  MappingSchema inheritance


def test_MSI_single_inheritance():
    from colander import Boolean
    from colander import Integer
    from colander import Schema
    from colander import SchemaNode
    from colander import String

    class Friend(Schema):
        rank = SchemaNode(Integer(), id='rank')
        name = SchemaNode(String(), id='name')
        serial = SchemaNode(Boolean(), id='serial2')

    class SpecialFriend(Friend):
        iwannacomefirst = SchemaNode(Integer(), id='iwannacomefirst2')

    class SuperSpecialFriend(SpecialFriend):
        iwannacomefirst = SchemaNode(String(), id='iwannacomefirst1')
        another = SchemaNode(String(), id='another')
        serial = SchemaNode(Integer(), id='serial1')

    inst = SuperSpecialFriend()

    result = [x.id for x in inst.children]

    assert result == ['rank', 'name', 'serial1', 'iwannacomefirst1', 'another']


def test_MSI_single_inheritance_with_insert_before():
    from colander import Boolean
    from colander import Integer
    from colander import Schema
    from colander import SchemaNode
    from colander import String

    class Friend(Schema):
        rank = SchemaNode(Integer(), id='rank')
        name = SchemaNode(String(), id='name')
        serial = SchemaNode(Boolean(), insert_before='name', id='serial2')

    class SpecialFriend(Friend):
        iwannacomefirst = SchemaNode(Integer(), id='iwannacomefirst2')

    class SuperSpecialFriend(SpecialFriend):
        iwannacomefirst = SchemaNode(
            String(), insert_before='rank', id='iwannacomefirst1'
        )
        another = SchemaNode(String(), id='another')
        serial = SchemaNode(Integer(), id='serial1')

    inst = SuperSpecialFriend()

    result = [x.id for x in inst.children]

    assert result == ['iwannacomefirst1', 'rank', 'serial1', 'name', 'another']


def test_MSI_single_inheritance2():
    from colander import Boolean
    from colander import Integer
    from colander import Schema
    from colander import SchemaNode
    from colander import String

    class One(Schema):
        a = SchemaNode(Integer(), id='a1')
        b = SchemaNode(Integer(), id='b1')
        d = SchemaNode(Integer(), id='d1')

    class Two(One):
        a = SchemaNode(String(), id='a2')
        c = SchemaNode(String(), id='c2')
        e = SchemaNode(String(), id='e2')

    class Three(Two):
        b = SchemaNode(Boolean(), id='b3')
        d = SchemaNode(Boolean(), id='d3')
        f = SchemaNode(Boolean(), id='f3')

    inst = Three()

    result = [x.id for x in inst.children]

    assert len(result) == 6
    assert result, ['a2', 'b3', 'd3', 'c2', 'e2' == 'f3']


def test_MSI_multiple_inheritance():
    from colander import Boolean
    from colander import Integer
    from colander import Schema
    from colander import SchemaNode
    from colander import String

    class One(Schema):
        a = SchemaNode(Integer(), id='a1')
        b = SchemaNode(Integer(), id='b1')
        d = SchemaNode(Integer(), id='d1')

    class Two(Schema):
        a = SchemaNode(String(), id='a2')
        c = SchemaNode(String(), id='c2')
        e = SchemaNode(String(), id='e2')

    class Three(Two, One):
        b = SchemaNode(Boolean(), id='b3')
        d = SchemaNode(Boolean(), id='d3')
        f = SchemaNode(Boolean(), id='f3')

    inst = Three()

    result = [x.id for x in inst.children]

    assert len(result) == 6
    assert result, ['a2', 'b3', 'd3', 'c2', 'e2' == 'f3']


def test_MSI_insert_before_failure():
    from colander import Integer
    from colander import Schema
    from colander import SchemaNode

    class One(Schema):
        a = SchemaNode(Integer())
        b = SchemaNode(Integer(), insert_before='c')

    with pytest.raises(KeyError):
        One()
