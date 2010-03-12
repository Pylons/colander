import pkg_resources
import itertools

def resolve_dotted(dottedname, package=None):
    if dottedname.startswith('.') or dottedname.startswith(':'):
        if not package:
            raise ImportError('name "%s" is irresolveable (no package)' %
                dottedname)
        if dottedname in ['.', ':']:
            dottedname = package.__name__
        else:
            dottedname = package.__name__ + dottedname
    return pkg_resources.EntryPoint.parse(
        'x=%s' % dottedname).load(False)

class Invalid(Exception):

    pos = None
    parent = None

    def __init__(self, struct, msg=None):
        Exception.__init__(self, struct, msg)
        self.struct = struct
        self.msg = msg
        self.subexceptions = []

    def add(self, error):
        error.parent = self
        self.subexceptions.append(error)

    def paths(self):
        def traverse(node, stack):
            stack.append(node)

            if not node.subexceptions:
                yield tuple(stack)

            for child in node.subexceptions:
                for path in traverse(child, stack):
                    yield path

            stack.pop()

        return traverse(self, [])

    def asdict(self):
        paths = self.paths()
        D = {}
        for path in paths:
            keyparts = []
            msgs = []
            for exc in path:
                exc.msg and msgs.append(exc.msg)
                if exc.parent is not None:
                    if isinstance(exc.parent.struct.typ, Positional):
                        val = exc.pos
                    else:
                        val = exc.struct.name
                    keyparts.append(str(val))
            D['.'.join(keyparts)] = '; '.join(msgs)
        return D

class All(object):
    def __init__(self, *validators):
        self.validators = validators

    def __call__(self, struct, value):
        msgs = []
        for validator in self.validators:
            try:
                validator(struct, value)
            except Invalid, e:
                msgs.append(e.msg)

        if msgs:
            raise Invalid(struct, msgs)

class Range(object):
    def __init__(self, min=None, max=None):
        self.min = min
        self.max = max

    def __call__(self, struct, value):
        if self.min is not None:
            if value < self.min:
                raise Invalid(
                    struct,
                    '%r is less than minimum value %r' % (value, self.min))

        if self.max is not None:
            if value > self.max:
                raise Invalid(
                    struct,
                    '%r is greater than maximum value %r' % (value, self.max))

class Mapping(object):
    """ A type which represents a mapping of names to data 
    structures. """
    def _validate(self, struct, value):
        if not hasattr(value, 'get'):
            raise Invalid(struct, '%r is not a mapping type' % value)
        return value

    def serialize(self, struct, value):
        value = self._validate(struct, value)
        result = {}

        error = None

        for num, substruct in enumerate(struct.structs):
            name = substruct.name
            subval = value.get(name)
            try:
                if subval is None:
                    if substruct.required and substruct.default is None:
                        raise Invalid(
                            substruct,
                            '%r is required but empty' % substruct.name)
                    result[name] = substruct.serialize(struct.default)
                else:
                    result[name] = substruct.serialize(subval)
            except Invalid, e:
                if error is None:
                    error = Invalid(substruct)
                e.pos = num
                error.add(e)

        if error is not None:
            raise error
                
        return result

    def deserialize(self, struct, value):
        value = self._validate(struct, value)

        error = None
        result = {}

        for num, substruct in enumerate(struct.structs):
            name = substruct.name
            subval = value.get(name)

            try:
                if subval is None:
                    if substruct.required and substruct.default is None:
                        raise Invalid(
                            substruct,
                            '%r is required but empty' % substruct.name)
                    result[name] = substruct.default
                else:
                    result[name] = substruct.deserialize(subval)
            except Invalid, e:
                if error is None:
                    error = Invalid(struct)
                e.pos = num
                error.add(e)

        if error is not None:
            raise error
                
        return result

class Positional(object):
    """
    Marker abstract base class meaning 'this type has children which
    should be addressed by position instead of name' (e.g. via seq[0],
    but never seq['name']).  This is consulted by Invalid.asdict when
    creating a dictionary representation of an error structure.
    """

class Tuple(Positional):
    """ A type which represents a fixed-length sequence of data
    structures, each one of which may be different as denoted by the
    types of the associated structure's children."""
    def _validate(self, struct, value):
        if not hasattr(value, '__iter__'):
            raise Invalid(struct, '%r is not an iterable value' % value)
        return list(value)

    def serialize(self, struct, value):
        value = self._validate(struct, value)

        error = None
        result = []

        for num, substruct in enumerate(struct.structs):
            try:
                subval = value[num]
            except IndexError:
                raise Invalid(struct, 'Wrong number of elements in %r' % value)
            try:
                result.append(substruct.serialize(subval))
            except Invalid, e:
                if error is None:
                    error = Invalid(struct)
                e.pos = num
                e.sequence_child = True
                error.add(e)
                
        if error:
            raise error

        return tuple(result)

    def deserialize(self, struct, value):
        value = self._validate(struct, value)

        error = None
        result = []

        for num, substruct in enumerate(struct.structs):
            try:
                subval = value[num]
            except IndexError:
                raise Invalid(struct, 'Wrong number of elements in %r' % value)
            try:
                result.append(substruct.deserialize(subval))
            except Invalid, e:
                if error is None:
                    error = Invalid(struct)
                e.pos = num
                e.sequence_child = True
                error.add(e)
                
        if error:
            raise error

        return tuple(result)

class Sequence(Positional):
    """ A type which represents a variable-length sequence of values,
    all of which must be of the same type as denoted by the type of
    the Structure instance ``substruct``"""
    def __init__(self, substruct):
        self.substruct = substruct

    def _validate(self, struct, value):
        if not hasattr(value, '__iter__'):
            raise Invalid(struct, '%r is not an iterable value' % value)
        return list(value)

    def serialize(self, struct, value):
        value = self._validate(struct, value)

        error = None
        result = []
        for num, subval in enumerate(value):
            try:
                result.append(self.substruct.serialize(subval))
            except Invalid, e:
                if error is None:
                    error = Invalid(struct)
                e.pos = num
                error.add(e)
                
        if error:
            raise error

        return result

    def deserialize(self, struct, value):
        value = self._validate(struct, value)

        error = None
        result = []
        for num, sub in enumerate(value):
            try:
                result.append(self.substruct.deserialize(sub))
            except Invalid, e:
                if error is None:
                    error = Invalid(struct)
                e.pos = num
                error.add(e)
                
        if error:
            raise error

        return result

class String(object):
    """ A type representing a Unicode string """
    def __init__(self, encoding='utf-8'):
        self.encoding = encoding
    
    def _validate(self, struct, value):
        try:
            if isinstance(value, unicode):
                return value
            return unicode(value, self.encoding)
        except:
            raise Invalid(struct, '%r is not a string' % value)

    def serialize(self, struct, value):
        decoded = self._validate(struct, value)
        return decoded.encode(struct.encoding)

    def deserialize(self, struct, value):
        return self._validate(struct, value)

class Integer(object):
    """ A type representing an integer """
    def _validate(self, struct, value):
        try:
            return int(value)
        except:
            raise Invalid(struct, '%r is not a number' % value)

    def serialize(self, struct, value):
        return str(self._validate(struct, value))

    def deserialize(self, struct, value):
        return self._validate(struct, value)

Int = Integer

class GlobalObject(object):
    """ A type representing an importable Python object """
    def __init__(self, package):
        self.package = package

    def serialize(self, struct, value):
        try:
            return value.__name__
        except AttributeError:
            raise Invalid(struct, '%r has no __name__' % value)
        
    def deserialize(self, struct, value):
        if not isinstance(value, basestring):
            raise Invalid(struct, '%r is not a global object specification')
        try:
            return resolve_dotted(value, package=self.package)
        except ImportError:
            raise Invalid(struct,
                          'The dotted name %r cannot be imported' % value)

class Structure(object):
    _counter = itertools.count()
    
    def __new__(cls, *arg, **kw):
        inst = object.__new__(cls)
        inst._order = cls._counter.next()
        return inst
        
    def __init__(self, typ, *structs, **kw):
        self.typ = typ
        self.validator = kw.get('validator', None)
        self.default = kw.get('default', None)
        self.required = kw.get('required', True)
        self.name = kw.get('name', '')
        self.structs = list(structs)

    def serialize(self, value):
        return self.typ.serialize(self, value)

    def deserialize(self, value):
        value = self.typ.deserialize(self, value)
        if self.validator is not None:
            self.validator(self, value)
        return value

    def add(self, struct):
        self.structs.append(struct)

class _SchemaMeta(type):
    def __init__(cls, name, bases, clsattrs):
        structs = []
        for name, value in clsattrs.items():
            if isinstance(value, Structure):
                value.name = name
                structs.append((value._order, value))
        cls.__schema_structures__ = structs
        # Combine all attrs from this class and its subclasses.
        extended = []
        for c in cls.__mro__:
            extended.extend(getattr(c, '__schema_structures__', []))
        # Sort the attrs to maintain the order as defined, and assign to the
        # class.
        extended.sort()
        cls.structs = [x[1] for x in extended]

class Schema(object):
    struct_type = Mapping
    __metaclass__ = _SchemaMeta

    def __new__(cls, *args, **kw):
        inst = object.__new__(Structure)
        inst.name = None
        inst._order = Structure._counter.next()
        struct = cls.struct_type(*args, **kw)
        inst.__init__(struct)
        for s in cls.structs:
            inst.add(s)
        return inst

MappingSchema = Schema

class SequenceSchema(Schema):
    struct_type = Sequence

class TupleSchema(Schema):
    struct_type = Tuple
    
    
        
