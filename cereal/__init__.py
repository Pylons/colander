import pkg_resources

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
        if self.msg is not None:
            raise ValueError(
                'Exceptions with a message cannot have subexceptions')
        error.parent = self
        self.subexceptions.append(error)

    def paths(self):
        # thanks chris rossi ;-)
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
        paths = list(self.paths())
        D = {}
        for path in paths:
            L = []
            msg = None
            for exc in path:
                msg = exc.msg
                if exc.parent is not None:
                    if isinstance(exc.parent.struct.typ, Positional):
                        L.append(str(exc.pos))
                    else:
                        L.append(exc.struct.name)
            D['.'.join(L)] = msg
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
    def _validate(self, struct, value):
        if not isinstance(value, dict):
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
    ``substruct``"""
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
    def __init__(self, name, typ, validator=None, default=None, required=True):
        self.typ = typ
        self.name = name
        self.validator = validator
        self.default = default
        self.required = required
        self.structs = []

    def serialize(self, value):
        return self.typ.serialize(self, value)

    def deserialize(self, value):
        value = self.typ.deserialize(self, value)
        if self.validator is not None:
            self.validator(self, value)
        return value

    def add(self, struct):
        self.structs.append(struct)

