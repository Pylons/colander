import unittest

def invalid_exc(func, *arg, **kw):
    from colander import Invalid
    try:
        func(*arg, **kw)
    except Invalid, e:
        return e
    else:
        raise AssertionError('Invalid not raised') # pragma: no cover

class TestInvalid(unittest.TestCase):
    def _makeOne(self, struct, msg=None, pos=None):
        from colander import Invalid
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
        from colander import Positional
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
        from colander import Positional
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
        from colander import All
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
        from colander import Range
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
        from colander import OneOf
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
        from colander import Mapping
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
        from colander import Tuple
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
        from colander import Sequence
        return Sequence(substruct)

    def test_alias(self):
        from colander import Seq
        from colander import Sequence
        self.assertEqual(Seq, Sequence)

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
        from colander import String
        return String(encoding)

    def test_alias(self):
        from colander import Str
        from colander import String
        self.assertEqual(Str, String)

    def test_deserialize_uncooperative(self):
        val = Uncooperative()
        struct = DummyStructure(None)
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, struct, val)
        self.failUnless(e.msg)

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

    def test_serialize_uncooperative(self):
        val = Uncooperative()
        struct = DummyStructure(None)
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, struct, val)
        self.failUnless(e.msg)

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

class TestInteger(unittest.TestCase):
    def _makeOne(self):
        from colander import Integer
        return Integer()

    def test_alias(self):
        from colander import Int
        from colander import Integer
        self.assertEqual(Int, Integer)

    def test_deserialize_fails(self):
        val = 'P'
        struct = DummyStructure(None)
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, struct, val)
        self.failUnless(e.msg)

    def test_deserialize_ok(self):
        val = '1'
        struct = DummyStructure(None)
        typ = self._makeOne()
        result = typ.deserialize(struct, val)
        self.assertEqual(result, 1)

    def test_serialize_fails(self):
        val = 'P'
        struct = DummyStructure(None)
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, struct, val)
        self.failUnless(e.msg)

    def test_serialize_ok(self):
        val = 1
        struct = DummyStructure(None)
        typ = self._makeOne()
        result = typ.serialize(struct, val)
        self.assertEqual(result, '1')

class TestFloat(unittest.TestCase):
    def _makeOne(self):
        from colander import Float
        return Float()

    def test_deserialize_fails(self):
        val = 'P'
        struct = DummyStructure(None)
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, struct, val)
        self.failUnless(e.msg)

    def test_deserialize_ok(self):
        val = '1.0'
        struct = DummyStructure(None)
        typ = self._makeOne()
        result = typ.deserialize(struct, val)
        self.assertEqual(result, 1.0)

    def test_serialize_fails(self):
        val = 'P'
        struct = DummyStructure(None)
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, struct, val)
        self.failUnless(e.msg)

    def test_serialize_ok(self):
        val = 1.0
        struct = DummyStructure(None)
        typ = self._makeOne()
        result = typ.serialize(struct, val)
        self.assertEqual(result, '1.0')

class TestBoolean(unittest.TestCase):
    def _makeOne(self):
        from colander import Boolean
        return Boolean()

    def test_alias(self):
        from colander import Bool
        from colander import Boolean
        self.assertEqual(Bool, Boolean)

    def test_deserialize(self):
        typ = self._makeOne()
        struct = DummyStructure(None)
        self.assertEqual(typ.deserialize(struct, 'false'), False)
        self.assertEqual(typ.deserialize(struct, 'FALSE'), False)
        self.assertEqual(typ.deserialize(struct, '0'), False)
        self.assertEqual(typ.deserialize(struct, 'true'), True)
        self.assertEqual(typ.deserialize(struct, 'other'), True)

    def test_deserialize_unstringable(self):
        typ = self._makeOne()
        struct = DummyStructure(None)
        e = invalid_exc(typ.deserialize, struct, Uncooperative())
        self.failUnless(e.msg.endswith('not a string'))

    def test_serialize(self):
        typ = self._makeOne()
        struct = DummyStructure(None)
        self.assertEqual(typ.serialize(struct, 1), 'true')
        self.assertEqual(typ.serialize(struct, True), 'true')
        self.assertEqual(typ.serialize(struct, None), 'false')
        self.assertEqual(typ.serialize(struct, False), 'false')

class TestGlobalObject(unittest.TestCase):
    def _makeOne(self, package=None):
        from colander import GlobalObject
        return GlobalObject(package)

    def test_zope_dottedname_style_resolve_absolute(self):
        typ = self._makeOne()
        result = typ._zope_dottedname_style(None,
            'colander.tests.TestGlobalObject')
        self.assertEqual(result, self.__class__)
        
    def test_zope_dottedname_style_irrresolveable_absolute(self):
        typ = self._makeOne()
        self.assertRaises(ImportError, typ._zope_dottedname_style, None,
            'colander.tests.nonexisting')

    def test__zope_dottedname_style_resolve_relative(self):
        import colander
        typ = self._makeOne(package=colander)
        result = typ._zope_dottedname_style(None, '.tests.TestGlobalObject')
        self.assertEqual(result, self.__class__)

    def test__zope_dottedname_style_resolve_relative_leading_dots(self):
        import colander
        typ = self._makeOne(package=colander.tests)
        result = typ._zope_dottedname_style(None, '..tests.TestGlobalObject')
        self.assertEqual(result, self.__class__)

    def test__zope_dottedname_style_resolve_relative_is_dot(self):
        import colander.tests
        typ = self._makeOne(package=colander.tests)
        result = typ._zope_dottedname_style(None, '.')
        self.assertEqual(result, colander.tests)

    def test__zope_dottedname_style_irresolveable_relative_is_dot(self):
        typ = self._makeOne()
        e = invalid_exc(typ._zope_dottedname_style, None, '.')
        self.assertEqual(
            e.msg,
            "relative name '.' irresolveable without package")

    def test_zope_dottedname_style_resolve_relative_nocurrentpackage(self):
        typ = self._makeOne()
        e = invalid_exc(typ._zope_dottedname_style, None, '.whatever')
        self.assertEqual(
            e.msg, "relative name '.whatever' irresolveable without package")

    def test_zope_dottedname_style_irrresolveable_relative(self):
        import colander.tests
        typ = self._makeOne(package=colander)
        self.assertRaises(ImportError, typ._zope_dottedname_style, None,
                          '.notexisting')

    def test__zope_dottedname_style_resolveable_relative(self):
        import colander
        typ = self._makeOne(package=colander)
        result = typ._zope_dottedname_style(None, '.tests')
        from colander import tests
        self.assertEqual(result, tests)

    def test__zope_dottedname_style_irresolveable_absolute(self):
        typ = self._makeOne()
        self.assertRaises(ImportError,
                          typ._zope_dottedname_style, None, 'colander.fudge.bar')

    def test__zope_dottedname_style_resolveable_absolute(self):
        typ = self._makeOne()
        result = typ._zope_dottedname_style(None,
                                            'colander.tests.TestGlobalObject')
        self.assertEqual(result, self.__class__)

    def test__pkg_resources_style_resolve_absolute(self):
        typ = self._makeOne()
        result = typ._pkg_resources_style(None,
            'colander.tests:TestGlobalObject')
        self.assertEqual(result, self.__class__)
        
    def test__pkg_resources_style_irrresolveable_absolute(self):
        typ = self._makeOne()
        self.assertRaises(ImportError, typ._pkg_resources_style, None,
            'colander.tests:nonexisting')

    def test__pkg_resources_style_resolve_relative_startswith_colon(self):
        import colander.tests
        typ = self._makeOne(package=colander.tests)
        result = typ._pkg_resources_style(None, ':TestGlobalObject')
        self.assertEqual(result, self.__class__)

    def test__pkg_resources_style_resolve_relative_startswith_dot(self):
        import colander
        typ = self._makeOne(package=colander)
        result = typ._pkg_resources_style(None, '.tests:TestGlobalObject')
        self.assertEqual(result, self.__class__)

    def test__pkg_resources_style_resolve_relative_is_dot(self):
        import colander.tests
        typ = self._makeOne(package=colander.tests)
        result = typ._pkg_resources_style(None, '.')
        self.assertEqual(result, colander.tests)
        
    def test__pkg_resources_style_resolve_relative_nocurrentpackage(self):
        typ = self._makeOne()
        self.assertRaises(ImportError, typ._pkg_resources_style, None,
                          '.whatever')

    def test__pkg_resources_style_irrresolveable_relative(self):
        import colander.tests
        typ = self._makeOne(package=colander)
        self.assertRaises(ImportError, typ._pkg_resources_style, None,
                          ':notexisting')

    def test_deserialize_not_a_string(self):
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, None, None)
        self.assertEqual(e.msg, "None is not a string")

    def test_deserialize_using_pkgresources_style(self):
        typ = self._makeOne()
        result = typ.deserialize(None, 'colander.tests:TestGlobalObject')
        self.assertEqual(result, self.__class__)

    def test_deserialize_using_zope_dottedname_style(self):
        typ = self._makeOne()
        result = typ.deserialize(None, 'colander.tests.TestGlobalObject')
        self.assertEqual(result, self.__class__)

    def test_deserialize_style_raises(self):
        typ = self._makeOne()
        e = invalid_exc(typ.deserialize, None, 'cant.be.found')
        self.assertEqual(e.msg,
                         "The dotted name 'cant.be.found' cannot be imported")

    def test_serialize_ok(self):
        import colander.tests
        typ = self._makeOne()
        result = typ.serialize(None, colander.tests)
        self.assertEqual(result, 'colander.tests')
        
    def test_serialize_fail(self):
        typ = self._makeOne()
        e = invalid_exc(typ.serialize, None, None)
        self.assertEqual(e.msg, 'None has no __name__')

class TestStructure(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from colander import Structure
        return Structure(*arg, **kw)

    def test_new_sets_order(self):
        structure = self._makeOne(None)
        self.failUnless(hasattr(structure, '_order'))

    def test_ctor(self):
        structure = self._makeOne(None, 0, validator=1, default=2, name=3)
        self.assertEqual(structure.typ, None)
        self.assertEqual(structure.structs, [0])
        self.assertEqual(structure.validator, 1)
        self.assertEqual(structure.default, 2)
        self.assertEqual(structure.name, 3)

    def test_required_true(self):
        structure = self._makeOne(None)
        self.assertEqual(structure.required, True)

    def test_required_false(self):
        structure = self._makeOne(None, default=1)
        self.assertEqual(structure.required, False)

    def test_deserialize_no_validator(self):
        typ = DummyType()
        structure = self._makeOne(typ)
        result = structure.deserialize(1)
        self.assertEqual(result, 1)

    def test_deserialize_with_validator(self):
        typ = DummyType()
        validator = DummyValidator(msg='Wrong')
        structure = self._makeOne(typ, validator=validator)
        e = invalid_exc(structure.deserialize, 1)
        self.assertEqual(e.msg, 'Wrong')

    def test_serialize(self):
        typ = DummyType()
        structure = self._makeOne(typ)
        result = structure.serialize(1)
        self.assertEqual(result, 1)

    def test_add(self):
        structure = self._makeOne(None)
        structure.add(1)
        self.assertEqual(structure.structs, [1])

class TestSchema(unittest.TestCase):
    def test_alias(self):
        from colander import Schema
        from colander import MappingSchema
        self.assertEqual(Schema, MappingSchema)

    def test_it(self):
        import colander
        class MySchema(colander.Schema):
            thing = colander.Structure(colander.String())
        structure = MySchema(unknown_keys='raise')
        self.failUnless(hasattr(structure, '_order'))
        self.assertEqual(structure.__class__, colander.Structure)
        self.assertEqual(structure.typ.__class__, colander.Mapping)
        self.assertEqual(structure.typ.unknown_keys, 'raise')
        self.assertEqual(structure.structs[0].typ.__class__, colander.String)
        
class TestSequenceSchema(unittest.TestCase):
    def test_it(self):
        import colander
        class MySchema(colander.SequenceSchema):
            pass
        inner = colander.Structure(colander.String())
        structure = MySchema(inner)
        self.failUnless(hasattr(structure, '_order'))
        self.assertEqual(structure.__class__, colander.Structure)
        self.assertEqual(structure.typ.__class__, colander.Sequence)
        self.assertEqual(structure.typ.struct, inner)

class TestTupleSchema(unittest.TestCase):
    def test_it(self):
        import colander
        class MySchema(colander.TupleSchema):
            thing = colander.Structure(colander.String())
        structure = MySchema()
        self.failUnless(hasattr(structure, '_order'))
        self.assertEqual(structure.__class__, colander.Structure)
        self.assertEqual(structure.typ.__class__, colander.Tuple)
        self.assertEqual(structure.structs[0].typ.__class__, colander.String)

class TestFunctional(object):
    def test_deserialize_ok(self):
        import colander.tests
        data = {
            'int':'10',
            'ob':'colander.tests',
            'seq':[('1', 's'),('2', 's'), ('3', 's'), ('4', 's')],
            'seq2':[{'key':'1', 'key2':'2'}, {'key':'3', 'key2':'4'}],
            'tup':('1', 's'),
            }
        schema = self._makeSchema()
        result = schema.deserialize(data)
        self.assertEqual(result['int'], 10)
        self.assertEqual(result['ob'], colander.tests)
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
        import colander

        integer = colander.Structure(
            colander.Integer(),
            name='int',
            validator=colander.Range(0, 10)
            )

        ob = colander.Structure(
            colander.GlobalObject(package=colander),
            name='ob',
            )

        tup = colander.Structure(
            colander.Tuple(),
            colander.Structure(
                colander.Integer(),
                name='tupint',
                ),
            colander.Structure(
                colander.String(),
                name='tupstring',
                ),
            name='tup',
            )

        seq = colander.Structure(
            colander.Sequence(tup),
            name='seq',
            )

        seq2 = colander.Structure(
            colander.Sequence(
                colander.Structure(
                    colander.Mapping(),
                    colander.Structure(
                        colander.Integer(),
                        name='key',
                        ),
                    colander.Structure(
                        colander.Integer(),
                        name='key2',
                        ),
                    name='mapping',
                    )
                ),
            name='seq2',
            )

        schema = colander.Structure(
            colander.Mapping(),
            integer,
            ob,
            tup,
            seq,
            seq2)

        return schema

class TestDeclarative(unittest.TestCase, TestFunctional):
    
    def _makeSchema(self):

        import colander

        class TupleSchema(colander.TupleSchema):
            tupint = colander.Structure(colander.Int())
            tupstring = colander.Structure(colander.String())

        class MappingSchema(colander.MappingSchema):
            key = colander.Structure(colander.Int())
            key2 = colander.Structure(colander.Int())

        class MainSchema(colander.MappingSchema):
            int = colander.Structure(colander.Int(),
                                     validator=colander.Range(0, 10))
            ob = colander.Structure(colander.GlobalObject(package=colander))
            seq = colander.Structure(colander.Sequence(TupleSchema()))
            tup = TupleSchema()
            seq2 = colander.SequenceSchema(MappingSchema())

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
        from colander import Invalid
        if self.exc:
            raise Invalid(self, self.exc)
        return val

    def serialize(self, val):
        from colander import Invalid
        if self.exc:
            raise Invalid(self, self.exc)
        return val
        
class DummyValidator(object):
    def __init__(self, msg=None):
        self.msg = msg

    def __call__(self, struct, value):
        from colander import Invalid
        if self.msg:
            raise Invalid(struct, self.msg)

class Uncooperative(object):
    def __str__(self):
        raise ValueError('I wont cooperate')

    __unicode__ = __str__
    
class DummyType(object):
    def serialize(self, struct, value):
        return value

    def deserialize(self, struct, value):
        return value
    
