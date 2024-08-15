import pytest


def imperative(name='schema'):
    import colander

    integer = colander.SchemaNode(
        colander.Integer(), name='int', validator=colander.Range(0, 10)
    )

    ob = colander.SchemaNode(
        colander.GlobalObject(package=colander), name='ob'
    )

    tup = colander.SchemaNode(
        colander.Tuple(),
        colander.SchemaNode(colander.Integer(), name='tupint'),
        colander.SchemaNode(colander.String(), name='tupstring'),
        name='tup',
    )

    seq = colander.SchemaNode(colander.Sequence(), tup, name='seq')

    seq2 = colander.SchemaNode(
        colander.Sequence(),
        colander.SchemaNode(
            colander.Mapping(),
            colander.SchemaNode(colander.Integer(), name='key'),
            colander.SchemaNode(colander.Integer(), name='key2'),
            name='mapping',
        ),
        name='seq2',
    )

    schema = colander.SchemaNode(
        colander.Mapping(), integer, ob, tup, seq, seq2, name=name
    )

    return schema


def declarative(name='schema'):
    import colander

    class TupleSchema(colander.TupleSchema):
        tupint = colander.SchemaNode(colander.Int())
        tupstring = colander.SchemaNode(colander.String())

    class MappingSchema(colander.MappingSchema):
        key = colander.SchemaNode(colander.Int())
        key2 = colander.SchemaNode(colander.Int())

    class SequenceOne(colander.SequenceSchema):
        tup = TupleSchema()

    class SequenceTwo(colander.SequenceSchema):
        mapping = MappingSchema()

    class MainSchema(colander.MappingSchema):
        int = colander.SchemaNode(
            colander.Int(), validator=colander.Range(0, 10)
        )
        ob = colander.SchemaNode(colander.GlobalObject(package=colander))
        seq = SequenceOne()
        tup = TupleSchema()
        seq2 = SequenceTwo()

    schema = MainSchema(name=name)
    return schema


def ultra_declarative(name='schema'):
    import colander

    class IntSchema(colander.SchemaNode):
        schema_type = colander.Int

    class StringSchema(colander.SchemaNode):
        schema_type = colander.String

    class TupleSchema(colander.TupleSchema):
        tupint = IntSchema()
        tupstring = StringSchema()

    class MappingSchema(colander.MappingSchema):
        key = IntSchema()
        key2 = IntSchema()

    class SequenceOne(colander.SequenceSchema):
        tup = TupleSchema()

    class SequenceTwo(colander.SequenceSchema):
        mapping = MappingSchema()

    class IntSchemaRanged(IntSchema):
        validator = colander.Range(0, 10)

    class GlobalObjectSchema(colander.SchemaNode):
        def schema_type(self):
            return colander.GlobalObject(package=colander)

    class MainSchema(colander.MappingSchema):
        int = IntSchemaRanged()
        ob = GlobalObjectSchema()
        seq = SequenceOne()
        tup = TupleSchema()
        seq2 = SequenceTwo()

    MainSchema.name = name

    schema = MainSchema()
    return schema


def with_instantiate(name='schema'):
    import colander

    # an unlikely usage, but goes to test passing
    # parameters to instantiation works
    @colander.instantiate(name=name)
    class schema(colander.MappingSchema):
        int = colander.SchemaNode(
            colander.Int(), validator=colander.Range(0, 10)
        )
        ob = colander.SchemaNode(colander.GlobalObject(package=colander))

        @colander.instantiate()
        class seq(colander.SequenceSchema):
            @colander.instantiate()
            class tup(colander.TupleSchema):
                tupint = colander.SchemaNode(colander.Int())
                tupstring = colander.SchemaNode(colander.String())

        @colander.instantiate()
        class tup(colander.TupleSchema):
            tupint = colander.SchemaNode(colander.Int())
            tupstring = colander.SchemaNode(colander.String())

        @colander.instantiate()
        class seq2(colander.SequenceSchema):
            @colander.instantiate()
            class mapping(colander.MappingSchema):
                key = colander.SchemaNode(colander.Int())
                key2 = colander.SchemaNode(colander.Int())

    return schema


@pytest.fixture(
    scope="module",
    params=[
        imperative,
        declarative,
        ultra_declarative,
        with_instantiate,
    ],
)
def schema_maker(request):
    return request.param


def test_deserialize_ok(schema_maker):
    import tests

    data = {
        'int': '10',
        'ob': 'tests',
        'seq': [('1', 's'), ('2', 's'), ('3', 's'), ('4', 's')],
        'seq2': [{'key': '1', 'key2': '2'}, {'key': '3', 'key2': '4'}],
        'tup': ('1', 's'),
    }
    schema = schema_maker()

    result = schema.deserialize(data)

    assert result['int'] == 10
    assert result['ob'] == tests
    assert result['seq'] == [(1, 's'), (2, 's'), (3, 's'), (4, 's')]
    assert result['seq2'] == [{'key': 1, 'key2': 2}, {'key': 3, 'key2': 4}]
    assert result['tup'] == (1, 's')


def test_flatten_ok(schema_maker):
    import tests

    appstruct = {
        'int': 10,
        'ob': tests,
        'seq': [(1, 's'), (2, 's'), (3, 's'), (4, 's')],
        'seq2': [{'key': 1, 'key2': 2}, {'key': 3, 'key2': 4}],
        'tup': (1, 's'),
    }
    schema = schema_maker()

    result = schema.flatten(appstruct)

    expected = {
        'schema.seq.2.tupstring': 's',
        'schema.seq2.0.key2': 2,
        'schema.ob': tests,
        'schema.seq2.1.key2': 4,
        'schema.seq.1.tupstring': 's',
        'schema.seq2.0.key': 1,
        'schema.seq.1.tupint': 2,
        'schema.seq.0.tupstring': 's',
        'schema.seq.3.tupstring': 's',
        'schema.seq.3.tupint': 4,
        'schema.seq2.1.key': 3,
        'schema.int': 10,
        'schema.seq.0.tupint': 1,
        'schema.tup.tupint': 1,
        'schema.tup.tupstring': 's',
        'schema.seq.2.tupint': 3,
    }

    for k, v in expected.items():
        assert result[k] == v
    for k, v in result.items():
        assert expected[k] == v


def test_flatten_mapping_has_no_name(schema_maker):
    import tests

    appstruct = {
        'int': 10,
        'ob': tests,
        'seq': [(1, 's'), (2, 's'), (3, 's'), (4, 's')],
        'seq2': [{'key': 1, 'key2': 2}, {'key': 3, 'key2': 4}],
        'tup': (1, 's'),
    }
    schema = schema_maker(name='')
    result = schema.flatten(appstruct)

    expected = {
        'seq.2.tupstring': 's',
        'seq2.0.key2': 2,
        'ob': tests,
        'seq2.1.key2': 4,
        'seq.1.tupstring': 's',
        'seq2.0.key': 1,
        'seq.1.tupint': 2,
        'seq.0.tupstring': 's',
        'seq.3.tupstring': 's',
        'seq.3.tupint': 4,
        'seq2.1.key': 3,
        'int': 10,
        'seq.0.tupint': 1,
        'tup.tupint': 1,
        'tup.tupstring': 's',
        'seq.2.tupint': 3,
    }

    for k, v in expected.items():
        assert result[k] == v
    for k, v in result.items():
        assert expected[k] == v


def test_unflatten_ok(schema_maker):
    import tests

    fstruct = {
        'schema.seq.2.tupstring': 's',
        'schema.seq2.0.key2': 2,
        'schema.ob': tests,
        'schema.seq2.1.key2': 4,
        'schema.seq.1.tupstring': 's',
        'schema.seq2.0.key': 1,
        'schema.seq.1.tupint': 2,
        'schema.seq.0.tupstring': 's',
        'schema.seq.3.tupstring': 's',
        'schema.seq.3.tupint': 4,
        'schema.seq2.1.key': 3,
        'schema.int': 10,
        'schema.seq.0.tupint': 1,
        'schema.tup.tupint': 1,
        'schema.tup.tupstring': 's',
        'schema.seq.2.tupint': 3,
    }
    schema = schema_maker()

    result = schema.unflatten(fstruct)

    expected = {
        'int': 10,
        'ob': tests,
        'seq': [(1, 's'), (2, 's'), (3, 's'), (4, 's')],
        'seq2': [{'key': 1, 'key2': 2}, {'key': 3, 'key2': 4}],
        'tup': (1, 's'),
    }

    for k, v in expected.items():
        assert result[k] == v

    for k, v in result.items():
        assert expected[k] == v


def test_unflatten_mapping_no_name(schema_maker):
    import tests

    fstruct = {
        'seq.2.tupstring': 's',
        'seq2.0.key2': 2,
        'ob': tests,
        'seq2.1.key2': 4,
        'seq.1.tupstring': 's',
        'seq2.0.key': 1,
        'seq.1.tupint': 2,
        'seq.0.tupstring': 's',
        'seq.3.tupstring': 's',
        'seq.3.tupint': 4,
        'seq2.1.key': 3,
        'int': 10,
        'seq.0.tupint': 1,
        'tup.tupint': 1,
        'tup.tupstring': 's',
        'seq.2.tupint': 3,
    }
    schema = schema_maker(name='')

    result = schema.unflatten(fstruct)

    expected = {
        'int': 10,
        'ob': tests,
        'seq': [(1, 's'), (2, 's'), (3, 's'), (4, 's')],
        'seq2': [{'key': 1, 'key2': 2}, {'key': 3, 'key2': 4}],
        'tup': (1, 's'),
    }

    for k, v in expected.items():
        assert result[k] == v

    for k, v in result.items():
        assert expected[k] == v


def test_flatten_unflatten_roundtrip(schema_maker):
    import tests

    appstruct = {
        'int': 10,
        'ob': tests,
        'seq': [(1, 's'), (2, 's'), (3, 's'), (4, 's')],
        'seq2': [{'key': 1, 'key2': 2}, {'key': 3, 'key2': 4}],
        'tup': (1, 's'),
    }
    schema = schema_maker(name='')

    assert schema.unflatten(schema.flatten(appstruct)) == appstruct


def test_set_value(schema_maker):
    import tests

    appstruct = {
        'int': 10,
        'ob': tests,
        'seq': [(1, 's'), (2, 's'), (3, 's'), (4, 's')],
        'seq2': [{'key': 1, 'key2': 2}, {'key': 3, 'key2': 4}],
        'tup': (1, 's'),
    }
    schema = schema_maker()

    schema.set_value(appstruct, 'seq2.1.key', 6)

    assert appstruct['seq2'][1] == {'key': 6, 'key2': 4}


def test_get_value(schema_maker):
    import tests

    appstruct = {
        'int': 10,
        'ob': tests,
        'seq': [(1, 's'), (2, 's'), (3, 's'), (4, 's')],
        'seq2': [{'key': 1, 'key2': 2}, {'key': 3, 'key2': 4}],
        'tup': (1, 's'),
    }
    schema = schema_maker()

    assert schema.get_value(appstruct, 'seq') == [
        (1, 's'),
        (2, 's'),
        (3, 's'),
        (4, 's'),
    ]
    assert schema.get_value(appstruct, 'seq2.1.key') == 3


def test_invalid_asdict(schema_maker):
    from colander import Invalid

    expected = {
        'schema.int': '20 is greater than maximum value 10',
        'schema.ob': 'The dotted name "no.way.this.exists" '
        'cannot be imported',
        'schema.seq.0.0': '"q" is not a number',
        'schema.seq.1.0': '"w" is not a number',
        'schema.seq.2.0': '"e" is not a number',
        'schema.seq.3.0': '"r" is not a number',
        'schema.seq2.0.key': '"t" is not a number',
        'schema.seq2.0.key2': '"y" is not a number',
        'schema.seq2.1.key': '"u" is not a number',
        'schema.seq2.1.key2': '"i" is not a number',
        'schema.tup.0': '"s" is not a number',
    }
    data = {
        'int': '20',
        'ob': 'no.way.this.exists',
        'seq': [('q', 's'), ('w', 's'), ('e', 's'), ('r', 's')],
        'seq2': [{'key': 't', 'key2': 'y'}, {'key': 'u', 'key2': 'i'}],
        'tup': ('s', 's'),
    }
    schema = schema_maker()

    with pytest.raises(Invalid) as exc:
        schema.deserialize(data)

    invalid = exc.value
    errors = invalid.asdict()
    assert errors == expected


def test_invalid_asdict_translation_callback(schema_maker):
    from colander import Invalid
    from translationstring import TranslationString

    expected = {
        'schema.int': 'translated',
        'schema.ob': 'translated',
        'schema.seq.0.0': 'translated',
        'schema.seq.1.0': 'translated',
        'schema.seq.2.0': 'translated',
        'schema.seq.3.0': 'translated',
        'schema.seq2.0.key': 'translated',
        'schema.seq2.0.key2': 'translated',
        'schema.seq2.1.key': 'translated',
        'schema.seq2.1.key2': 'translated',
        'schema.tup.0': 'translated',
    }
    data = {
        'int': '20',
        'ob': 'no.way.this.exists',
        'seq': [('q', 's'), ('w', 's'), ('e', 's'), ('r', 's')],
        'seq2': [{'key': 't', 'key2': 'y'}, {'key': 'u', 'key2': 'i'}],
        'tup': ('s', 's'),
    }
    schema = schema_maker()

    def translation_function(string):
        return TranslationString('translated')

    with pytest.raises(Invalid) as exc:
        schema.deserialize(data)

    invalid = exc.value
    errors = invalid.asdict(translate=translation_function)
    assert errors == expected
