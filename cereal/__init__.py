import itertools

class _missing(object):
    pass

class Invalid(Exception):
    """
    An exception raised by data types and validators indicating that
    the value for a particular structure was not valid.
    """
    pos = None
    parent = None

    def __init__(self, struct, msg=None):
        Exception.__init__(self, struct, msg)
        self.struct = struct
        self.msg = msg
        self.children = []

    def add(self, exc):
        # not an API
        exc.parent = self
        self.children.append(exc)

    def keyname(self):
        # not an API
        if self.parent and isinstance(self.parent.struct.typ, Positional):
            return str(self.pos)
        return str(self.struct.name)

    def paths(self):
        """ Return all paths through the exception graph  """
        def traverse(node, stack):
            stack.append(node)

            if not node.children:
                yield tuple(stack)

            for child in node.children:
                for path in traverse(child, stack):
                    yield path

            stack.pop()

        return traverse(self, [])

    def asdict(self):
        """ Return a dictionary containing an error report for this
        exception"""
        paths = self.paths()
        errors = {}
        for path in paths:
            keyparts = []
            msgs = []
            for exc in path:
                exc.msg and msgs.append(exc.msg)
                keyname = exc.keyname()
                keyname and keyparts.append(keyname)
            errors['.'.join(keyparts)] = '; '.join(msgs)
        return errors

class All(object):
    """ Composite validator which succeeds if none of its
    subvalidators raises an :class:`cereal.Invalid` exception"""
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
    """ Validator which succeeds if the value it is passed is greater
    or equal to ``min`` and less than or equal to ``max``.  If ``min``
    is not specified, or is specified as ``None``, no lower bound
    exists.  If ``max`` is not specified, or is specified as ``None``,
    no upper bound exists."""
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

class OneOf(object):
    """ Validator which succeeds if the value passed to it is one of
    a fixed set of values """
    def __init__(self, values):
        self.values = values

    def __call__(self, struct, value):
        if not value in self.values:
            raise Invalid(struct, '%r is not one of %r' % (value, self.values))

class Mapping(object):
    """ A type which represents a mapping of names to structures.

    The substructures of the :class:`cereal.Structure` that represents
    this type imply the named keys and values in the mapping.

    The constructor of a mapping type accepts a single optional
    keyword argument named ``unknown_keys``.  By default, this
    argument is ``ignore``.

    The potential values of ``unknown_keys`` are:

    - ``ignore`` means that keys that are not present in the schema
      associated with this type will be ignored during
      deserialization.

    - ``raise`` will cause a :exc:`cereal.Invalid` exception to
      be raised when unknown keys are present during deserialization.

    - ``preserve`` will preserve the 'raw' unknown keys and values in
      the returned data structure during deserialization.
    """

    def __init__(self, unknown_keys='ignore'):
        if not unknown_keys in ['ignore', 'raise', 'preserve']:
            raise ValueError(
                'unknown_keys argument must be one of "ignore", "raise", '
                'or "preserve"')
        self.unknown_keys = unknown_keys
        
    def _validate(self, struct, value):
        try:
            return dict(value)
        except Exception, e:
            raise Invalid(struct, '%r is not a mapping type: %s' % (value, e))

    def deserialize(self, struct, value):
        value = self._validate(struct, value)

        error = None
        result = {}

        for num, substruct in enumerate(struct.structs):
            name = substruct.name
            subval = value.pop(name, _missing)

            try:
                if subval is _missing:
                    if substruct.required:
                        raise Invalid(
                            substruct,
                            '%r is required but missing' % substruct.name)
                    result[name] = substruct.default
                else:
                    result[name] = substruct.deserialize(subval)
            except Invalid, e:
                if error is None:
                    error = Invalid(struct)
                e.pos = num
                error.add(e)

        if self.unknown_keys == 'raise':
            if value:
                raise Invalid(struct,
                              'Unrecognized keys in mapping: %r' % value)

        elif self.unknown_keys == 'preserve':
            result.update(value)

        if error is not None:
            raise error
                
        return result

    def serialize(self, struct, value):
        value = self._validate(struct, value)
        result = {}

        error = None

        for num, substruct in enumerate(struct.structs):
            name = substruct.name
            subval = value.pop(name, _missing)
            try:
                if subval is _missing:
                    if substruct.required:
                        raise Invalid(
                            substruct,
                            '%r is required but missing' % substruct.name)
                    result[name] = substruct.serialize(substruct.default)
                else:
                    result[name] = substruct.serialize(subval)
            except Invalid, e:
                if error is None:
                    error = Invalid(substruct)
                e.pos = num
                error.add(e)

        if self.unknown_keys == 'raise':
            if value:
                raise Invalid(struct,
                              'Unrecognized keys in mapping: %r' % value)

        elif self.unknown_keys == 'preserve':
            result.update(value)

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
    """ A type which represents a fixed-length sequence of structures.

    The substructures of the :class:`cereal.Structure` that
    represents this type imply the positional elements of the tuple.
    """
    def _validate(self, struct, value):
        if not hasattr(value, '__iter__'):
            raise Invalid(struct, '%r is not an iterable value' % value)
        return list(value)

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

class Sequence(Positional):
    """ A type which represents a variable-length sequence of
    structures, all of which must be of the same type as denoted by
    the type of the :class:`cereal.Structure` instance ``substruct``.

    The substructures of the :class:`cereal.Structure` that represents
    this type are ignored.
    """
    def __init__(self, substruct):
        self.substruct = substruct

    def _validate(self, struct, value):
        if not hasattr(value, '__iter__'):
            raise Invalid(struct, '%r is not an iterable value' % value)
        return list(value)

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

Seq = Sequence

class String(object):
    """ A type representing a Unicode string.  This type constructor
    accepts a single argument ``encoding``, representing the encoding
    which should be applied to object serialization.  It defaults to
    ``utf-8`` if not provided.

    The substructures of the :class:`cereal.Structure` that represents
    this type are ignored.
    """
    def __init__(self, encoding='utf-8'):
        self.encoding = encoding
    
    def _validate(self, struct, value):
        try:
            if isinstance(value, unicode):
                return value
            return unicode(value, self.encoding)
        except:
            raise Invalid(struct, '%r is not a string' % value)

    def deserialize(self, struct, value):
        return self._validate(struct, value)

    def serialize(self, struct, value):
        decoded = self._validate(struct, value)
        return decoded.encode(struct.encoding)

Str = String

class Integer(object):
    """ A type representing an integer.

    The substructures of the :class:`cereal.Structure` that represents
    this type are ignored.
    """
    def _validate(self, struct, value):
        try:
            return int(value)
        except:
            raise Invalid(struct, '%r is not a number' % value)

    def deserialize(self, struct, value):
        return self._validate(struct, value)

    def serialize(self, struct, value):
        return str(self._validate(struct, value))

Int = Integer

class Boolean(object):
    """ A type representing a boolean object.

    During deserialization, a value in the set (``true``, ``yes``,
    ``y``, ``on``, ``t``, ``1``) will be considered ``True``.
    Anything else is considered ``False``. Case is ignored.

    Serialization will produce ``true`` or ``false`` based on the
    value.

    The substructures of the :class:`cereal.Structure` that represents
    this type are ignored.
    """
    
    def deserialize(self, struct, value):
        if not isinstance(value, basestring):
            raise Invalid(struct, '%r is not a string' % value)
        value = value.lower()
        if value in ('true', 'yes', 'y', 'on', 't', '1'):
            return True
        return False

    def serialize(self, struct, value):
        return value and 'true' or 'false'

Bool = Boolean

class GlobalObject(object):
    """ A type representing an importable Python object.  This type
    serializes 'global' Python objects (objects which can be imported)
    to dotted Python names.  The constructor accepts a single argument
    named ``package`` which should be a Python module or package
    object; it is used when 'relative' dotted names are supplied (ones
    which start with a dot) as the package which the import should be
    considered relative to.

    The substructures of the :class:`cereal.Structure` that represents
    this type are ignored.
    """
    def __init__(self, package):
        self.package = package

    def deserialize(self, struct, value):
        import pkg_resources
        if not isinstance(value, basestring):
            raise Invalid(struct, '%r is not a global object specification')
        try:
            if value.startswith('.') or value.startswith(':'):
                if not self.package:
                    raise ImportError(
                        'name "%s" is irresolveable (no package)' % value)
                if value in ['.', ':']:
                    value = self.package.__name__
                else:
                    value = self.package.__name__ + value
            return pkg_resources.EntryPoint.parse(
                'x=%s' % value).load(False)
        except ImportError:
            raise Invalid(struct,
                          'The dotted name %r cannot be imported' % value)

    def serialize(self, struct, value):
        try:
            return value.__name__
        except AttributeError:
            raise Invalid(struct, '%r has no __name__' % value)

class Structure(object):
    """
    Fundamental building block of schemas.

    The constructor accepts these arguments:

    - ``typ`` (required): The 'type' for this structure.  It should be
      an instance of a class that implements the
      :class:`cereal.interfaces.Type` interface.

    - ``structs``: a sequence of substructures.  If the substructures
      of this structure are not known at construction time, they can
      later be added via the ``add`` method.

    - ``name``: The name of this structure.

    - ``default``: The default value for this structure; if it is not
      provided, this structure has no default value and it will be
      considered 'required' (the ``required`` attribute will be True).

    - ``validator``: Optional validator for this structure.  It should be
      an object that implements the
      :class:`cereal.interfaces.Validator` interface.
    """
    
    _counter = itertools.count()
    
    def __new__(cls, *arg, **kw):
        inst = object.__new__(cls)
        inst._order = cls._counter.next()
        return inst
        
    def __init__(self, typ, *structs, **kw):
        self.typ = typ
        self.validator = kw.get('validator', None)
        self.default = kw.get('default', _missing)
        self.name = kw.get('name', '')
        self.structs = list(structs)

    @property
    def required(self):
        """ Property which returns true if this structure is required in the
        schema """
        return self.default is _missing

    def deserialize(self, value):
        """ Derialize the value based on the schema represented by this
        structure """
        value = self.typ.deserialize(self, value)
        if self.validator is not None:
            self.validator(self, value)
        return value

    def serialize(self, value):
        """ Serialize the value based on the schema represented by this
        structure """
        return self.typ.serialize(self, value)

    def add(self, struct):
        """ Add a substructure to this structure """
        self.structs.append(struct)

Struct = Structure

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
