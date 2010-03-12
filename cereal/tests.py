import unittest

def invalid_exc(func, *arg, **kw):
    from cereal import Invalid
    try:
        func(*arg, **kw)
    except Invalid, e:
        return e
    else:
        raise AssertionError('Invalid not raised') # pragma: no cover

class TestInvalid(unittest.TestCase):
    def _makeOne(self, struct, msg=None, pos=None):
        from cereal import Invalid
        exc = Invalid(struct, msg)
        exc.pos = pos
        return exc

    def test_ctor(self):
        exc = self._makeOne(None, 'msg')
        self.assertEqual(exc.struct, None)
        self.assertEqual(exc.msg, 'msg')
        self.assertEqual(exc.children, [])

    def test_add(self):
        exc = self._makeOne(None, 'msg')
        other = Dummy()
        exc.add(other)
        self.assertEqual(other.parent, exc)
        self.assertEqual(exc.children, [other])

    def test__keyname_no_parent(self):
        struct = DummyStructure(None, name='name')
        exc = self._makeOne(None, '')
        exc.struct = struct
        self.assertEqual(exc._keyname(), 'name')

    def test__keyname_positional_parent(self):
        from cereal import Positional
        parent = Dummy()
        parent.struct = DummyStructure(Positional())
        exc = self._makeOne(None, '')
        exc.parent = parent
        exc.pos = 2
        self.assertEqual(exc._keyname(), '2')

    def test__keyname_nonpositional_parent(self):
        parent = Dummy()
        parent.struct = DummyStructure(None)
        exc = self._makeOne(None, 'me')
        exc.parent = parent
        exc.pos = 2
        exc.struct = DummyStructure(None, name='name')
        self.assertEqual(exc._keyname(), 'name')

    def test_paths(self):
        exc1 = self._makeOne(None, 'exc1')
        exc2 = self._makeOne(None, 'exc2') 
        exc3 = self._makeOne(None, 'exc3')
        exc4 = self._makeOne(None, 'exc4')
        exc1.add(exc2)
        exc2.add(exc3)
        exc1.add(exc4)
        paths = list(exc1.paths())
        self.assertEqual(paths, [(exc1, exc2, exc3), (exc1, exc4)])

    def test_asdict(self):
        from cereal import Positional
        struct1 = DummyStructure(None, 'struct1')
        struct2 = DummyStructure(Positional(), 'struct2')
        struct3 = DummyStructure(Positional(), 'struct3')
        struct4 = DummyStructure(Positional(), 'struct4')
        exc1 = self._makeOne(struct1, 'exc1', pos=1)
        exc2 = self._makeOne(struct2, 'exc2', pos=2) 
        exc3 = self._makeOne(struct3, 'exc3', pos=3)
        exc4 = self._makeOne(struct4, 'exc4', pos=4)
        exc1.add(exc2)
        exc2.add(exc3)
        exc1.add(exc4)
        d = exc1.asdict()
        self.assertEqual(d, {'struct1.struct2.3': 'exc1; exc2; exc3',
                             'struct1.struct4': 'exc1; exc4'})


class TestAll(unittest.TestCase):
    def _makeOne(self, validators):
        from cereal import All
        return All(*validators)

    def test_success(self):
        validator1 = DummyValidator()
        validator2 = DummyValidator()
        validator = self._makeOne([validator1, validator2])
        self.assertEqual(validator(None, None), None)

    def test_failure(self):
        validator1 = DummyValidator('msg1')
        validator2 = DummyValidator('msg2')
        validator = self._makeOne([validator1, validator2])
        e = invalid_exc(validator, None, None)
        self.assertEqual(e.msg, ['msg1', 'msg2'])

class TestRange(unittest.TestCase):
    def _makeOne(self, min=None, max=None):
        from cereal import Range
        return Range(min=min, max=max)

    def test_success_no_bounds(self):
        validator = self._makeOne()
        self.assertEqual(validator(None, 1), None)

    def test_success_upper_bound_only(self):
        validator = self._makeOne(max=1)
        self.assertEqual(validator(None, -1), None)

    def test_success_minimum_bound_only(self):
        validator = self._makeOne(min=0)
        self.assertEqual(validator(None, 1), None)

    def test_success_min_and_max(self):
        validator = self._makeOne(min=1, max=1)
        self.assertEqual(validator(None, 1), None)

    def test_min_failure(self):
        validator = self._makeOne(min=1)
        e = invalid_exc(validator, None, 0)
        self.assertEqual(e.msg, '0 is less than minimum value 1')

    def test_max_failure(self):
        validator = self._makeOne(max=1)
        e = invalid_exc(validator, None, 2)
        self.assertEqual(e.msg, '2 is greater than maximum value 1')

class TestOneOf(unittest.TestCase):
    def _makeOne(self, values):
        from cereal import OneOf
        return OneOf(values)

    def test_success(self):
        validator = self._makeOne([1])
        self.assertEqual(validator(None, 1), None)

    def test_failure(self):
        validator = self._makeOne([1])
        e = invalid_exc(validator, None, None)
        self.assertEqual(e.msg, 'None is not one of [1]')

class TestMapping(unittest.TestCase):
    def _makeOne(self, unknown_keys='ignore'):
        from cereal import Mapping
        return Mapping(unknown_keys=unknown_keys)

    def test_ctor_bad_unknown_keys(self):
        self.assertRaises(ValueError, self._makeOne, 'badarg')

    def test_ctor_good_unknown_keys(self):
        try:
            self._makeOne('ignore')
            self._makeOne('raise')
            self._makeOne('preserve')
        except ValueError, e: # pragma: no cover
            raise AssertionError(e)

    def test_deserialize_not_a_mapping(self):
        struct = DummyStructure(None)
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, struct, None)
        self.assertEqual(
            e.msg,
            'None is not a mapping type: iteration over non-sequence')

    def test_deserialize_no_substructs(self):
        struct = DummyStructure(None)
        typ = self._makeOne()
        result = typ.deserialize(struct, {})
        self.assertEqual(result, {})

    def test_deserialize_ok(self):
        struct = DummyStructure(None)
        struct.structs = [DummyStructure(None, name='a')]
        typ = self._makeOne()
        result = typ.deserialize(struct, {'a':1})
        self.assertEqual(result, {'a':1})

    def test_deserialize_unknown_keys_raise(self):
        struct = DummyStructure(None)
        struct.structs = [DummyStructure(None, name='a')]
        typ = self._makeOne('raise')
        e = invalid_exc(typ.deserialize, struct, {'a':1, 'b':2})
        self.assertEqual(e.msg, "Unrecognized keys in mapping: {'b': 2}")

    def test_deserialize_unknown_keys_preserve(self):
        struct = DummyStructure(None)
        struct.structs = [DummyStructure(None, name='a')]
        typ = self._makeOne('preserve')
        result = typ.deserialize(struct, {'a':1, 'b':2})
        self.assertEqual(result, {'a':1, 'b':2})

    def test_deserialize_substructs_raise(self):
        struct = DummyStructure(None)
        struct.structs = [
            DummyStructure(None, name='a', exc='Wrong 2'),
            DummyStructure(None, name='b', exc='Wrong 2'),
            ]
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, struct, {'a':1, 'b':2})
        self.assertEqual(e.msg, None)
        self.assertEqual(len(e.children), 2)

    def test_deserialize_substruct_missing_default(self):
        struct = DummyStructure(None)
        struct.structs = [
            DummyStructure(None, name='a'),
            DummyStructure(None, name='b', default='abc'),
            ]
        typ = self._makeOne()
        result = typ.deserialize(struct, {'a':1})
        self.assertEqual(result, {'a':1, 'b':'abc'})

    def test_deserialize_substruct_missing_nodefault(self):
        struct = DummyStructure(None)
        struct.structs = [
            DummyStructure(None, name='a'),
            DummyStructure(None, name='b'),
            ]
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, struct, {'a':1})
        self.assertEqual(e.children[0].msg, "'b' is required but missing")

    def test_serialize_not_a_mapping(self):
        struct = DummyStructure(None)
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, struct, None)
        self.assertEqual(
            e.msg,
            'None is not a mapping type: iteration over non-sequence')

    def test_serialize_no_substructs(self):
        struct = DummyStructure(None)
        typ = self._makeOne()
        result = typ.serialize(struct, {})
        self.assertEqual(result, {})

    def test_serialize_ok(self):
        struct = DummyStructure(None)
        struct.structs = [DummyStructure(None, name='a')]
        typ = self._makeOne()
        result = typ.serialize(struct, {'a':1})
        self.assertEqual(result, {'a':1})

    def test_serialize_unknown_keys_raise(self):
        struct = DummyStructure(None)
        struct.structs = [DummyStructure(None, name='a')]
        typ = self._makeOne('raise')
        e = invalid_exc(typ.serialize, struct, {'a':1, 'b':2})
        self.assertEqual(e.msg, "Unrecognized keys in mapping: {'b': 2}")

    def test_serialize_unknown_keys_preserve(self):
        struct = DummyStructure(None)
        struct.structs = [DummyStructure(None, name='a')]
        typ = self._makeOne('preserve')
        result = typ.serialize(struct, {'a':1, 'b':2})
        self.assertEqual(result, {'a':1, 'b':2})

    def test_serialize_substructs_raise(self):
        struct = DummyStructure(None)
        struct.structs = [
            DummyStructure(None, name='a', exc='Wrong 2'),
            DummyStructure(None, name='b', exc='Wrong 2'),
            ]
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, struct, {'a':1, 'b':2})
        self.assertEqual(e.msg, None)
        self.assertEqual(len(e.children), 2)

    def test_serialize_substruct_missing_default(self):
        struct = DummyStructure(None)
        struct.structs = [
            DummyStructure(None, name='a'),
            DummyStructure(None, name='b', default='abc'),
            ]
        typ = self._makeOne()
        result = typ.serialize(struct, {'a':1})
        self.assertEqual(result, {'a':1, 'b':'abc'})

    def test_serialize_substruct_missing_nodefault(self):
        struct = DummyStructure(None)
        struct.structs = [
            DummyStructure(None, name='a'),
            DummyStructure(None, name='b'),
            ]
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, struct, {'a':1})
        self.assertEqual(e.children[0].msg, "'b' is required but missing")

class TestTuple(unittest.TestCase):
    def _makeOne(self):
        from cereal import Tuple
        return Tuple()

    def test_deserialize_not_iterable(self):
        struct = DummyStructure(None)
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, struct, None)
        self.assertEqual(
            e.msg,
            'None is not iterable')
        self.assertEqual(e.struct, struct)

    def test_deserialize_no_substructs(self):
        struct = DummyStructure(None)
        typ = self._makeOne()
        result = typ.deserialize(struct, ())
        self.assertEqual(result, ())

    def test_deserialize_ok(self):
        struct = DummyStructure(None)
        struct.structs = [DummyStructure(None, name='a')]
        typ = self._makeOne()
        result = typ.deserialize(struct, ('a',))
        self.assertEqual(result, ('a',))

    def test_deserialize_toobig(self):
        struct = DummyStructure(None)
        struct.structs = [DummyStructure(None, name='a')]
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, struct, ('a','b'))
        self.assertEqual(e.msg,
           "('a', 'b') has an incorrect number of elements (expected 1, was 2)")

    def test_deserialize_toosmall(self):
        struct = DummyStructure(None)
        struct.structs = [DummyStructure(None, name='a')]
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, struct, ())
        self.assertEqual(e.msg,
           "() has an incorrect number of elements (expected 1, was 0)")

    def test_deserialize_substructs_raise(self):
        struct = DummyStructure(None)
        struct.structs = [
            DummyStructure(None, name='a', exc='Wrong 2'),
            DummyStructure(None, name='b', exc='Wrong 2'),
            ]
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, struct, ('1', '2'))
        self.assertEqual(e.msg, None)
        self.assertEqual(len(e.children), 2)

    def test_serialize_not_iterable(self):
        struct = DummyStructure(None)
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, struct, None)
        self.assertEqual(
            e.msg,
            'None is not iterable')
        self.assertEqual(e.struct, struct)

    def test_serialize_no_substructs(self):
        struct = DummyStructure(None)
        typ = self._makeOne()
        result = typ.serialize(struct, ())
        self.assertEqual(result, ())

    def test_serialize_ok(self):
        struct = DummyStructure(None)
        struct.structs = [DummyStructure(None, name='a')]
        typ = self._makeOne()
        result = typ.serialize(struct, ('a',))
        self.assertEqual(result, ('a',))

    def test_serialize_toobig(self):
        struct = DummyStructure(None)
        struct.structs = [DummyStructure(None, name='a')]
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, struct, ('a','b'))
        self.assertEqual(e.msg,
           "('a', 'b') has an incorrect number of elements (expected 1, was 2)")

    def test_serialize_toosmall(self):
        struct = DummyStructure(None)
        struct.structs = [DummyStructure(None, name='a')]
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, struct, ())
        self.assertEqual(e.msg,
           "() has an incorrect number of elements (expected 1, was 0)")

    def test_serialize_substructs_raise(self):
        struct = DummyStructure(None)
        struct.structs = [
            DummyStructure(None, name='a', exc='Wrong 2'),
            DummyStructure(None, name='b', exc='Wrong 2'),
            ]
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, struct, ('1', '2'))
        self.assertEqual(e.msg, None)
        self.assertEqual(len(e.children), 2)

class TestSequence(unittest.TestCase):
    def _makeOne(self, substruct):
        from cereal import Sequence
        return Sequence(substruct)

    def test_deserialize_not_iterable(self):
        struct = DummyStructure(None)
        typ = self._makeOne(struct)
        e = invalid_exc(typ.deserialize, struct, None)
        self.assertEqual(
            e.msg,
            'None is not iterable')
        self.assertEqual(e.struct, struct)

    def test_deserialize_no_substructs(self):
        struct = DummyStructure(None)
        typ = self._makeOne(struct)
        result = typ.deserialize(struct, ())
        self.assertEqual(result, [])

    def test_deserialize_ok(self):
        struct = DummyStructure(None)
        struct.structs = [DummyStructure(None, name='a')]
        typ = self._makeOne(struct)
        result = typ.deserialize(struct, ('a',))
        self.assertEqual(result, ['a'])

    def test_deserialize_substructs_raise(self):
        struct = DummyStructure(None, exc='Wrong')
        typ = self._makeOne(struct)
        e = invalid_exc(typ.deserialize, struct, ('1', '2'))
        self.assertEqual(e.msg, None)
        self.assertEqual(len(e.children), 2)

    def test_serialize_not_iterable(self):
        struct = DummyStructure(None)
        typ = self._makeOne(struct)
        e = invalid_exc(typ.serialize, struct, None)
        self.assertEqual(
            e.msg,
            'None is not iterable')
        self.assertEqual(e.struct, struct)

    def test_serialize_no_substructs(self):
        struct = DummyStructure(None)
        typ = self._makeOne(struct)
        result = typ.serialize(struct, ())
        self.assertEqual(result, [])

    def test_serialize_ok(self):
        struct = DummyStructure(None)
        struct.structs = [DummyStructure(None, name='a')]
        typ = self._makeOne(struct)
        result = typ.serialize(struct, ('a',))
        self.assertEqual(result, ['a'])

    def test_serialize_substructs_raise(self):
        struct = DummyStructure(None, exc='Wrong')
        typ = self._makeOne(struct)
        e = invalid_exc(typ.serialize, struct, ('1', '2'))
        self.assertEqual(e.msg, None)
        self.assertEqual(len(e.children), 2)

class TestString(unittest.TestCase):
    def _makeOne(self, encoding='utf-8'):
        from cereal import String
        return String(encoding)

    def test_deserialize_unicode(self):
        uni = u'\xf8'
        struct = DummyStructure(None)
        typ = self._makeOne()
        result = typ.deserialize(struct, uni)
        self.assertEqual(result, uni)

    def test_deserialize_from_utf8(self):
        utf8 = '\xc3\xb8'
        uni = u'\xf8'
        struct = DummyStructure(None)
        typ = self._makeOne()
        result = typ.deserialize(struct, utf8)
        self.assertEqual(result, uni)

    def test_deserialize_from_utf16(self):
        utf16 = '\xff\xfe\xf8\x00'
        uni = u'\xf8'
        struct = DummyStructure(None)
        typ = self._makeOne('utf-16')
        result = typ.deserialize(struct, utf16)
        self.assertEqual(result, uni)

    def test_serialize_to_utf8(self):
        utf8 = '\xc3\xb8'
        uni = u'\xf8'
        struct = DummyStructure(None)
        typ = self._makeOne()
        result = typ.serialize(struct, uni)
        self.assertEqual(result, utf8)

    def test_serialize_to_utf16(self):
        utf16 = '\xff\xfe\xf8\x00'
        uni = u'\xf8'
        struct = DummyStructure(None)
        typ = self._makeOne('utf-16')
        result = typ.serialize(struct, uni)
        self.assertEqual(result, utf16)

class TestFunctional(object):
    def test_deserialize_ok(self):
        import cereal.tests
        data = {
            'int':'10',
            'ob':'cereal.tests',
            'seq':[('1', 's'),('2', 's'), ('3', 's'), ('4', 's')],
            'seq2':[{'key':'1', 'key2':'2'}, {'key':'3', 'key2':'4'}],
            'tup':('1', 's'),
            }
        schema = self._makeSchema()
        result = schema.deserialize(data)
        self.assertEqual(result['int'], 10)
        self.assertEqual(result['ob'], cereal.tests)
        self.assertEqual(result['seq'],
                         [(1, 's'), (2, 's'), (3, 's'), (4, 's')])
        self.assertEqual(result['seq2'],
                         [{'key':1, 'key2':2}, {'key':3, 'key2':4}])
        self.assertEqual(result['tup'], (1, 's'))
        
    def test_invalid_asdict(self):
        expected = {
            'int': '20 is greater than maximum value 10',
            'ob': "The dotted name 'no.way.this.exists' cannot be imported",
            'seq.0.0': "'q' is not a number",
            'seq.1.0': "'w' is not a number",
            'seq.2.0': "'e' is not a number",
            'seq.3.0': "'r' is not a number",
            'seq2.0.key': "'t' is not a number",
            'seq2.0.key2': "'y' is not a number",
            'seq2.1.key': "'u' is not a number",
            'seq2.1.key2': "'i' is not a number",
            'tup.0': "'s' is not a number"}
        data = {
            'int':'20',
            'ob':'no.way.this.exists',
            'seq':[('q', 's'),('w', 's'), ('e', 's'), ('r', 's')],
            'seq2':[{'key':'t', 'key2':'y'}, {'key':'u', 'key2':'i'}],
            'tup':('s', 's'),
            }
        schema = self._makeSchema()
        e = invalid_exc(schema.deserialize, data)
        errors = e.asdict()
        self.assertEqual(errors, expected)

class TestImperative(unittest.TestCase, TestFunctional):
    
    def _makeSchema(self):
        import cereal

        integer = cereal.Structure(
            cereal.Integer(),
            name='int',
            validator=cereal.Range(0, 10)
            )

        ob = cereal.Structure(
            cereal.GlobalObject(package=cereal),
            name='ob',
            )

        tup = cereal.Structure(
            cereal.Tuple(),
            cereal.Structure(
                cereal.Integer(),
                name='tupint',
                ),
            cereal.Structure(
                cereal.String(),
                name='tupstring',
                ),
            name='tup',
            )

        seq = cereal.Structure(
            cereal.Sequence(tup),
            name='seq',
            )

        seq2 = cereal.Structure(
            cereal.Sequence(
                cereal.Structure(
                    cereal.Mapping(),
                    cereal.Structure(
                        cereal.Integer(),
                        name='key',
                        ),
                    cereal.Structure(
                        cereal.Integer(),
                        name='key2',
                        ),
                    name='mapping',
                    )
                ),
            name='seq2',
            )

        schema = cereal.Structure(
            cereal.Mapping(),
            integer,
            ob,
            tup,
            seq,
            seq2)

        return schema

class TestDeclarative(unittest.TestCase, TestFunctional):
    
    def _makeSchema(self):

        import cereal

        class TupleSchema(cereal.TupleSchema):
            tupint = cereal.Structure(cereal.Int())
            tupstring = cereal.Structure(cereal.String())

        class MappingSchema(cereal.MappingSchema):
            key = cereal.Structure(cereal.Int())
            key2 = cereal.Structure(cereal.Int())

        class MainSchema(cereal.MappingSchema):
            int = cereal.Structure(cereal.Int(), validator=cereal.Range(0, 10))
            ob = cereal.Structure(cereal.GlobalObject(package=cereal))
            seq = cereal.Structure(cereal.Sequence(TupleSchema()))
            tup = TupleSchema()
            seq2 = cereal.SequenceSchema(MappingSchema())

        schema = MainSchema()
        return schema

class Dummy(object):
    pass

class DummyStructure(object):
    def __init__(self, typ, name='', exc=None, default=None):
        self.typ = typ
        self.name = name
        self.exc = exc
        self.required = default is None
        self.default = default
        self.structs = []

    def deserialize(self, val):
        from cereal import Invalid
        if self.exc:
            raise Invalid(self, self.exc)
        return val

    def serialize(self, val):
        from cereal import Invalid
        if self.exc:
            raise Invalid(self, self.exc)
        return val
        
class DummyValidator(object):
    def __init__(self, msg=None):
        self.msg = msg

    def __call__(self, struct, value):
        from cereal import Invalid
        if self.msg:
            raise Invalid(struct, self.msg)
