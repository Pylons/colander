import itertools

class _missing(object):
    pass

class Invalid(Exception):
    """
    An exception raised by data types and validators indicating that
    the value for a particular structure was not valid.

    The constructor receives a mandatory ``struct`` argument.  This
    must be an instance of the :class:`colander.Structure` class.

    The constructor also receives an optional ``msg`` keyword
    argument, defaulting to ``None``.  The ``msg`` argument is a
    freeform field indicating the error circumstance.
    """
    pos = None
    parent = None

    def __init__(self, struct, msg=None):
        Exception.__init__(self, struct, msg)
        self.struct = struct
        self.msg = msg
        self.children = []

    def add(self, exc):
        """ Add a child exception; ``exc`` must be an instance of
        :class:`colander.Invalid`"""
        exc.parent = self
        self.children.append(exc)

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

    def _keyname(self):
        if self.parent and isinstance(self.parent.struct.typ, Positional):
            return str(self.pos)
        return str(self.struct.name)

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
                keyname = exc._keyname()
                keyname and keyparts.append(keyname)
            errors['.'.join(keyparts)] = '; '.join(msgs)
        return errors

class All(object):
    """ Composite validator which succeeds if none of its
    subvalidators raises an :class:`colander.Invalid` exception"""
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

    The substructures of the :class:`colander.Structure` that wraps
    this type imply the named keys and values in the mapping.

    The constructor of a mapping type accepts a single optional
    keyword argument named ``unknown_keys``.  By default, this
    argument is ``ignore``.

    The potential values of ``unknown_keys`` are:

    - ``ignore`` means that keys that are not present in the schema
      associated with this type will be ignored during
      deserialization.

    - ``raise`` will cause a :exc:`colander.Invalid` exception to be
      raised when unknown keys are present during deserialization.

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

    def _impl(self, struct, value, callback, default_callback):
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
                    result[name] = default_callback(substruct)
                else:
                    result[name] = callback(substruct, subval)
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

    def deserialize(self, struct, value):
        def callback(substruct, subval):
            return substruct.deserialize(subval)
        def default_callback(substruct):
            return substruct.default
        return self._impl(struct, value, callback, default_callback)

    def serialize(self, struct, value):
        def callback(substruct, subval):
            return substruct.serialize(subval)
        def default_callback(substruct):
            return substruct.serialize(substruct.default)
        return self._impl(struct, value, callback, default_callback)

class Positional(object):
    """
    Marker abstract base class meaning 'this type has children which
    should be addressed by position instead of name' (e.g. via seq[0],
    but never seq['name']).  This is consulted by Invalid.asdict when
    creating a dictionary representation of an error structure.
    """

class Tuple(Positional):
    """ A type which represents a fixed-length sequence of structures.

    The substructures of the :class:`colander.Structure` that wraps
    this type imply the positional elements of the tuple in the order
    they are added.

    This type is willing to serialize and deserialized iterables that,
    when converted to a tuple, have the same number of elements as the
    number of the associated structure's substructures.
    """
    def _validate(self, struct, value):
        if not hasattr(value, '__iter__'):
            raise Invalid(struct, '%r is not iterable' % value)

        valuelen, structlen = len(value), len(struct.structs)

        if valuelen != structlen:
            raise Invalid(
                struct,
                ('%s has an incorrect number of elements '
                 '(expected %s, was %s)' % (value, structlen, valuelen)))

        return list(value)

    def _impl(self, struct, value, callback):
        value = self._validate(struct, value)
        error = None
        result = []

        for num, substruct in enumerate(struct.structs):
            subval = value[num]
            try:
                result.append(callback(substruct, subval))
            except Invalid, e:
                if error is None:
                    error = Invalid(struct)
                e.pos = num
                error.add(e)
                
        if error is not None:
            raise error

        return tuple(result)

    def deserialize(self, struct, value):
        def callback(substruct, subval):
            return substruct.deserialize(subval)
        return self._impl(struct, value, callback)

    def serialize(self, struct, value):
        def callback(substruct, subval):
            return substruct.serialize(subval)
        return self._impl(struct, value, callback)

class Sequence(Positional):
    """
    A type which represents a variable-length sequence of structures,
    all of which must be of the same type.  This type is defined by
    the the :class:`colander.Structure` instance passed to the
    constructor as ``struct``.

    The ``struct`` argument to this type's constructor is required.

    The substructures of the :class:`colander.Structure` that wraps
    this type are ignored.
    """
    def __init__(self, struct):
        self.struct = struct

    def _validate(self, struct, value):
        if not hasattr(value, '__iter__'):
            raise Invalid(struct, '%r is not iterable' % value)
        return list(value)

    def _impl(self, struct, value, callback):
        value = self._validate(struct, value)

        error = None
        result = []
        for num, subval in enumerate(value):
            try:
                result.append(callback(self.struct, subval))
            except Invalid, e:
                if error is None:
                    error = Invalid(struct)
                e.pos = num
                error.add(e)
                
        if error is not None:
            raise error

        return result

    def deserialize(self, struct, value):
        def callback(substruct, subval):
            return substruct.deserialize(subval)
        return self._impl(struct, value, callback)

    def serialize(self, struct, value):
        def callback(substruct, subval):
            return substruct.serialize(subval)
        return self._impl(struct, value, callback)

Seq = Sequence

default_encoding = 'utf-8'

class String(object):
    """ A type representing a Unicode string.  This type constructor
    accepts a single argument ``encoding``, representing the encoding
    which should be applied to object serialization.  It defaults to
    ``utf-8`` if not provided.

    The substructures of the :class:`colander.Structure` that wraps
    this type are ignored.
    """
    def __init__(self, encoding=None):
        self.encoding = encoding
    
    def deserialize(self, struct, value):
        try:
            if isinstance(value, unicode):
                return value
            else:
                return unicode(str(value), self.encoding or default_encoding)
        except Exception, e:
            raise Invalid(struct, '%r is not a string: %s' % (value, e))

    def serialize(self, struct, value):
        try:
            return unicode(value).encode(self.encoding or default_encoding)
        except Exception, e:
            raise Invalid(struct,
                          '%r is cannot be serialized to str: %s' % (value, e))

Str = String

class Integer(object):
    """ A type representing an integer.

    The substructures of the :class:`colander.Structure` that wraps
    this type are ignored.
    """
    def deserialize(self, struct, value):
        try:
            return int(value)
        except Exception:
            raise Invalid(struct, '%r is not a number' % value)

    def serialize(self, struct, value):
        try:
            return str(int(value))
        except Exception:
            raise Invalid(struct, '%r is not a number' % value)

Int = Integer

class Float(object):
    """ A type representing a float.

    The substructures of the :class:`colander.Structure` that wraps
    this type are ignored.
    """
    def deserialize(self, struct, value):
        try:
            return float(value)
        except Exception:
            raise Invalid(struct, '%r is not a number' % value)

    def serialize(self, struct, value):
        try:
            return str(float(value))
        except Exception:
            raise Invalid(struct, '%r is not a number' % value)

Int = Integer

class Boolean(object):
    """ A type representing a boolean object.

    During deserialization, a value in the set (``false``, ``0``) will
    be considered ``False``.  Anything else is considered
    ``True``. Case is ignored.

    Serialization will produce ``true`` or ``false`` based on the
    value.

    The substructures of the :class:`colander.Structure` that wraps
    this type are ignored.
    """
    
    def deserialize(self, struct, value):
        try:
            value = str(value)
        except:
            raise Invalid(struct, '%r is not a string' % value)
        value = value.lower()
        if value in ('false', '0'):
            return False
        return True

    def serialize(self, struct, value):
        return value and 'true' or 'false'

Bool = Boolean

class GlobalObject(object):
    """ A type representing an importable Python object.  This type
    serializes 'global' Python objects (objects which can be imported)
    to dotted Python names.

    Two dotted name styles are supported during deserialization:

    - ``pkg_resources``-style dotted names where non-module attributes
      of a module are separated from the rest of the path using a ':'
      e.g. ``package.module:attr``.

    - ``zope.dottedname``-style dotted names where non-module
      attributes of a module are separated from the rest of the path
      using a '.' e.g. ``package.module.attr``.

    These styles can be used interchangeably.  If the serialization
    contains a ``:`` (colon), the ``pkg_resources`` resolution
    mechanism will be chosen, otherwise the ``zope.dottedname``
    resolution mechanism will be chosen.

    The constructor accepts a single argument named ``package`` which
    should be a Python module or package object; it is used when
    *relative* dotted names are supplied to the ``deserialize``
    method.  A serialization which has a ``.`` (dot) or ``:`` (colon)
    as its first character is treated as relative.  E.g. if
    ``.minidom`` is supplied to ``deserialize``, and the ``package``
    argument to this type was passed the ``xml`` module object, the
    resulting import would be for ``xml.minidom``.  If a relative
    package name is supplied to ``deserialize``, and no ``package``
    was supplied to the constructor, an :exc:`colander.Invalid` error
    will be raised.

    The substructures of the :class:`colander.Structure` that wraps
    this type are ignored.
    """
    def __init__(self, package):
        self.package = package

    def _pkg_resources_style(self, struct, value):
        """ package.module:attr style """
        import pkg_resources
        if value.startswith('.') or value.startswith(':'):
            if not self.package:
                raise ImportError(
                    'relative name %r irresolveable without package' % value)
            if value in ['.', ':']:
                value = self.package.__name__
            else:
                value = self.package.__name__ + value
        return pkg_resources.EntryPoint.parse(
            'x=%s' % value).load(False)

    def _zope_dottedname_style(self, struct, value):
        """ package.module.attr style """
        module = self.package and self.package.__name__ or None
        if value == '.':
            if self.package is None:
                raise Invalid(
                    struct,
                    "relative name %r irresolveable without package" % value)
            name = module.split('.')
        else:
            name = value.split('.')
            if not name[0]:
                if module is None:
                    raise Invalid(
                        struct,
                        "relative name %r irresolveable without package" %
                        value)
                module = module.split('.')
                name.pop(0)
                while not name[0]:
                    module.pop()
                    name.pop(0)
                name = module + name

        used = name.pop(0)
        found = __import__(used)
        for n in name:
            used += '.' + n
            try:
                found = getattr(found, n)
            except AttributeError:
                __import__(used)
                found = getattr(found, n)

        return found

    def deserialize(self, struct, value):
        if not isinstance(value, basestring):
            raise Invalid(struct, '%r is not a string' % value)
        try:
            if ':' in value:
                return self._pkg_resources_style(struct, value)
            else:
                return self._zope_dottedname_style(struct, value)
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
      :class:`colander.interfaces.Type` interface.

    - ``structs``: a sequence of substructures.  If the substructures
      of this structure are not known at construction time, they can
      later be added via the ``add`` method.

    - ``name``: The name of this structure.

    - ``default``: The default value for this structure; if it is not
      provided, this structure has no default value and it will be
      considered 'required' (the ``required`` attribute will be True).

    - ``validator``: Optional validator for this structure.  It should
      be an object that implements the
      :class:`colander.interfaces.Validator` interface.
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
