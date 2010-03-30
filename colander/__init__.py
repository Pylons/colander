import datetime
import itertools
import iso8601
import pprint

class _missing(object):
    pass

class Invalid(Exception):
    """
    An exception raised by data types and validators indicating that
    the value for a particular node was not valid.

    The constructor receives a mandatory ``node`` argument.  This must
    be an instance of the :class:`colander.SchemaNode` class.

    The constructor also receives an optional ``msg`` keyword
    argument, defaulting to ``None``.  The ``msg`` argument is a
    freeform field indicating the error circumstance.
    """
    pos = None
    parent = None

    def __init__(self, node, msg=None):
        Exception.__init__(self, node, msg)
        self.node = node
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
        if self.parent and isinstance(self.parent.node.typ, Positional):
            return str(self.pos)
        return str(self.node.name)

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

    def __str__(self):
        """ Return a pretty-formatted string representation of the
        result of an execution of this exception's ``asdict`` method"""
        return pprint.pformat(self.asdict())

class All(object):
    """ Composite validator which succeeds if none of its
    subvalidators raises an :class:`colander.Invalid` exception"""
    def __init__(self, *validators):
        self.validators = validators

    def __call__(self, node, value):
        msgs = []
        for validator in self.validators:
            try:
                validator(node, value)
            except Invalid, e:
                msgs.append(e.msg)

        if msgs:
            raise Invalid(node, msgs)

class Range(object):
    """ Validator which succeeds if the value it is passed is greater
    or equal to ``min`` and less than or equal to ``max``.  If ``min``
    is not specified, or is specified as ``None``, no lower bound
    exists.  If ``max`` is not specified, or is specified as ``None``,
    no upper bound exists."""
    def __init__(self, min=None, max=None):
        self.min = min
        self.max = max

    def __call__(self, node, value):
        if self.min is not None:
            if value < self.min:
                raise Invalid(
                    node,
                    '%s is less than minimum value %s' % (value, self.min))

        if self.max is not None:
            if value > self.max:
                raise Invalid(
                    node,
                    '%s is greater than maximum value %s' % (value, self.max))

class Length(object):
    """ Validator which succeeds if the value passed to it has a
    length between a minimum and maximum.  The value is most often a
    string."""
    def __init__(self, min=None, max=None):
        self.min = min
        self.max = max

    def __call__(self, node, value):
        if self.min is not None:
            if len(value) < self.min:
                raise Invalid(
                    node,
                    'Shorter than minimum length %s' % self.min)

        if self.max is not None:
            if len(value) > self.max:
                raise Invalid(
                    node,
                    'Longer than maximum length %s' % self.max)


class OneOf(object):
    """ Validator which succeeds if the value passed to it is one of
    a fixed set of values """
    def __init__(self, values):
        self.values = values

    def __call__(self, node, value):
        if not value in self.values:
            raise Invalid(node, '"%s" is not one of %s' % (
                value, ', '.join(['%s' % x for x in self.values])))

class Mapping(object):
    """ A type which represents a mapping of names to nodes.

    The subnodes of the :class:`colander.SchemaNode` that wraps
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
        
    def _validate(self, node, value):
        try:
            return dict(value)
        except Exception, e:
            raise Invalid(node, '%r is not a mapping type: %s' % (value, e))

    def _impl(self, node, value, callback, default_callback):
        value = self._validate(node, value)

        error = None
        result = {}

        for num, subnode in enumerate(node.children):
            name = subnode.name
            subval = value.pop(name, _missing)

            try:
                if subval is _missing:
                    if subnode.required:
                        raise Invalid(
                            subnode,
                            '"%s" is required but missing' % subnode.name)
                    result[name] = default_callback(subnode)
                else:
                    result[name] = callback(subnode, subval)
            except Invalid, e:
                if error is None:
                    error = Invalid(node)
                e.pos = num
                error.add(e)

        if self.unknown_keys == 'raise':
            if value:
                raise Invalid(node,
                              'Unrecognized keys in mapping: %r' % value)

        elif self.unknown_keys == 'preserve':
            result.update(value)

        if error is not None:
            raise error
                
        return result

    def deserialize(self, node, value):
        def callback(subnode, subval):
            return subnode.deserialize(subval)
        def default_callback(subnode):
            return subnode.default
        return self._impl(node, value, callback, default_callback)

    def serialize(self, node, value):
        def callback(subnode, subval):
            return subnode.serialize(subval)
        def default_callback(subnode):
            return subnode.serialize(subnode.default)
        return self._impl(node, value, callback, default_callback)

class Positional(object):
    """
    Marker abstract base class meaning 'this type has children which
    should be addressed by position instead of name' (e.g. via seq[0],
    but never seq['name']).  This is consulted by Invalid.asdict when
    creating a dictionary representation of an error tree.
    """

class Tuple(Positional):
    """ A type which represents a fixed-length sequence of nodes.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type imply the positional elements of the tuple in the order
    they are added.

    This type is willing to serialize and deserialized iterables that,
    when converted to a tuple, have the same number of elements as the
    number of the associated node's subnodes.
    """
    def _validate(self, node, value):
        if not hasattr(value, '__iter__'):
            raise Invalid(node, '%r is not iterable' % value)

        valuelen, nodelen = len(value), len(node.children)

        if valuelen != nodelen:
            raise Invalid(
                node,
                ('%s has an incorrect number of elements '
                 '(expected %s, was %s)' % (value, nodelen, valuelen)))

        return list(value)

    def _impl(self, node, value, callback):
        value = self._validate(node, value)
        error = None
        result = []

        for num, subnode in enumerate(node.children):
            subval = value[num]
            try:
                result.append(callback(subnode, subval))
            except Invalid, e:
                if error is None:
                    error = Invalid(node)
                e.pos = num
                error.add(e)
                
        if error is not None:
            raise error

        return tuple(result)

    def deserialize(self, node, value):
        def callback(subnode, subval):
            return subnode.deserialize(subval)
        return self._impl(node, value, callback)

    def serialize(self, node, value):
        def callback(subnode, subval):
            return subnode.serialize(subval)
        return self._impl(node, value, callback)

class Sequence(Positional):
    """
    A type which represents a variable-length sequence of nodes,
    all of which must be of the same type.

    The type of the first subnode of the
    :class:`colander.SchemaNode` that wraps this type is considered the
    sequence type.

    The optional ``accept_scalar`` argument to this type's constructor
    indicates that if the value found during serialization or
    deserialization does not have an ``__iter__`` method or is a
    mapping type, that the value will be converted to a length-one
    list.  If ``accept_scalar`` is ``False`` (the default), and the
    value does not have an ``__iter__`` method, an
    :exc:`colander.Invalid` error will be raised during serialization
    and deserialization.

    """
    def __init__(self, accept_scalar=False):
        self.accept_scalar = accept_scalar

    def _validate(self, node, value):
        if hasattr(value, '__iter__') and not hasattr(value, 'get'):
            return list(value)
        if self.accept_scalar:
            return [value]
        else:
            raise Invalid(node, '%r is not iterable' % value)

    def _impl(self, node, value, callback):
        value = self._validate(node, value)

        error = None
        result = []
        for num, subval in enumerate(value):
            try:
                result.append(callback(node.children[0], subval))
            except Invalid, e:
                if error is None:
                    error = Invalid(node)
                e.pos = num
                error.add(e)
                
        if error is not None:
            raise error

        return result

    def deserialize(self, node, value):
        def callback(subnode, subval):
            return subnode.deserialize(subval)
        return self._impl(node, value, callback)

    def serialize(self, node, value):
        def callback(subnode, subval):
            return subnode.serialize(subval)
        return self._impl(node, value, callback)

Seq = Sequence

default_encoding = 'utf-8'

class String(object):
    """ A type representing a Unicode string.  This type constructor
    accepts a single argument ``encoding``, representing the encoding
    which should be applied to object serialization.  It defaults to
    ``utf-8`` if not provided.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type are ignored.
    """
    def __init__(self, encoding=None):
        self.encoding = encoding
    
    def deserialize(self, node, value):
        try:
            if not isinstance(value, unicode):
                value = unicode(str(value), self.encoding or default_encoding)
        except Exception, e:
            raise Invalid(node, '%r is not a string: %s' % (value, e))
        if not value:
            if node.required:
                raise Invalid(node, 'Required')
            value = node.default
        return value

    def serialize(self, node, value):
        try:
            return unicode(value).encode(self.encoding or default_encoding)
        except Exception, e:
            raise Invalid(node,
                          '%r is cannot be serialized to str: %s' % (value, e))

Str = String

class Integer(object):
    """ A type representing an integer.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type are ignored.
    """
    def deserialize(self, node, value):
        try:
            return int(value)
        except Exception:
            if value == '':
                if node.required:
                    raise Invalid(node, 'Required')
                return node.default
            raise Invalid(node, '"%s" is not a number' % value)

    def serialize(self, node, value):
        try:
            return str(int(value))
        except Exception:
            raise Invalid(node, '"%s" is not a number' % value)

Int = Integer

class Float(object):
    """ A type representing a float.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type are ignored.
    """
    def deserialize(self, node, value):
        try:
            return float(value)
        except Exception:
            if value == '':
                if node.required:
                    raise Invalid(node, 'Required')
                return node.default
            raise Invalid(node, '"%s" is not a number' % value)

    def serialize(self, node, value):
        try:
            return str(float(value))
        except Exception:
            raise Invalid(node, '"%s" is not a number' % value)

Int = Integer

class Boolean(object):
    """ A type representing a boolean object.

    During deserialization, a value in the set (``false``, ``0``) will
    be considered ``False``.  Anything else is considered
    ``True``. Case is ignored.

    Serialization will produce ``true`` or ``false`` based on the
    value.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type are ignored.
    """
    
    def deserialize(self, node, value):
        try:
            value = str(value)
        except:
            raise Invalid(node, '%r is not a string' % value)
        if not value:
            if node.required:
                raise Invalid(node, 'Required')
            value = node.default
        value = value.lower()
        if value in ('false', '0'):
            return False
        return True

    def serialize(self, node, value):
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

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type are ignored.
    """
    def __init__(self, package):
        self.package = package

    def _pkg_resources_style(self, node, value):
        """ package.module:attr style """
        import pkg_resources
        if value.startswith('.') or value.startswith(':'):
            if not self.package:
                raise Invalid(
                    node,
                    'relative name "%s" irresolveable without package' % value)
            if value in ['.', ':']:
                value = self.package.__name__
            else:
                value = self.package.__name__ + value
        return pkg_resources.EntryPoint.parse(
            'x=%s' % value).load(False)

    def _zope_dottedname_style(self, node, value):
        """ package.module.attr style """
        module = self.package and self.package.__name__ or None
        if value == '.':
            if self.package is None:
                raise Invalid(
                    node,
                    'relative name "%s" irresolveable without package' % value)
            name = module.split('.')
        else:
            name = value.split('.')
            if not name[0]:
                if module is None:
                    raise Invalid(
                        node,
                        'relative name "%s" irresolveable without package' %
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

    def deserialize(self, node, value):
        if not isinstance(value, basestring):
            raise Invalid(node, '"%s" is not a string' % value)
        try:
            if ':' in value:
                return self._pkg_resources_style(node, value)
            else:
                return self._zope_dottedname_style(node, value)
        except ImportError:
            raise Invalid(node,
                          'The dotted name "%s" cannot be imported' % value)

    def serialize(self, node, value):
        try:
            return value.__name__
        except AttributeError:
            raise Invalid(node, '%r has no __name__' % value)

class DateTime(object):
    """ A type representing a Python ``datetime.datetime`` object.

    This type serializes python ``datetime.datetime`` objects to a
    `ISO8601 <http://en.wikipedia.org/wiki/ISO_8601>`_ string format.
    The format includes the date, the time, and the timezone of the
    datetime.

    The constructor accepts a single argument named ``default_tzinfo``
    which should be a Python ``tzinfo`` object; by default it is None,
    meaning that the default tzinfo will be equivalent to UTC (Zulu
    time).  The ``default_tzinfo`` tzinfo object is used to convert
    'naive' datetimes to a timezone-aware representation during
    serialization.

    For convenience, this type is also willing to coerce
    ``datetime.date`` objects to a DateTime ISO string representation
    during serialization.  It does so by using midnight of the day as
    the time, and uses the ``default_tzinfo`` to give the
    serialization a timezone.

    Likewise, for convenience, during deserialization, this type will
    convert ``YYYY-MM-DD`` ISO8601 values to a datetime object.  It
    does so by using midnight of the day as the time, and uses the
    ``default_tzinfo`` to give the serialization a timezone.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type are ignored.
    """
    def __init__(self, default_tzinfo=None):
        if default_tzinfo is None:
            default_tzinfo = iso8601.iso8601.Utc()
        self.default_tzinfo = default_tzinfo
        
    def serialize(self, node, value):
        if type(value) is datetime.date: # cant use isinstance; dt subs date
            value = datetime.datetime.combine(value, datetime.time())
        if not isinstance(value, datetime.datetime):
            raise Invalid(node, '%r is not a datetime object' % value)
        if value.tzinfo is None:
            value = value.replace(tzinfo=self.default_tzinfo)
        return value.isoformat()

    def deserialize(self, node, value):
        try:
            result = iso8601.parse_date(value)
        except (iso8601.ParseError, TypeError), e:
            try:
                year, month, day = map(int, value.split('-', 2))
                result = datetime.datetime(year, month, day,
                                           tzinfo=self.default_tzinfo)
            except Exception, e:
                raise Invalid(node,
                              '%s cannot be parsed as an iso8601 date: %s' %
                              (value, e))
        return result

class Date(object):
    """ A type representing a Python ``datetime.date`` object.

    This type serializes python ``datetime.date`` objects to a
    `ISO8601 <http://en.wikipedia.org/wiki/ISO_8601>`_ string format.
    The format includes the date only.

    The constructor accepts no arguments.

    For convenience, this type is also willing to coerce
    ``datetime.datetime`` objects to a date-only ISO string
    representation during serialization.  It does so by stripping off
    any time information, converting the ``datetime.datetime`` into a
    date before serializing.

    Likewise, for convenience, this type is also willing to coerce ISO
    representations that contain time info into a ``datetime.date``
    object during deserialization.  It does so by throwing away any
    time information related to the serialized value during
    deserialization.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type are ignored.
    """
    def serialize(self, node, value):
        if isinstance(value, datetime.datetime):
            value = value.date()
        if not isinstance(value, datetime.date):
            raise Invalid(node, '%r is not a date object' % value)
        return value.isoformat()

    def deserialize(self, node, value):
        try:
            result = iso8601.parse_date(value)
            result = result.date()
        except (iso8601.ParseError, TypeError):
            try:
                year, month, day = map(int, value.split('-', 2))
                result = datetime.date(year, month, day)
            except Exception, e:
                raise Invalid(node,
                              '%s cannot be parsed as an iso8601 date: %s' %
                              (value, e))
        return result

class SchemaNode(object):
    """
    Fundamental building block of schemas.

    The constructor accepts these arguments:

    - ``typ`` (required): The 'type' for this node.  It should be an
      instance of a class that implements the
      :class:`colander.interfaces.Type` interface.

    - ``children``: a sequence of subnodes.  If the subnodes of this
      node are not known at construction time, they can later be added
      via the ``add`` method.

    - ``name``: The name of this node.

    - ``default``: The default value for this node; if it is not
      provided, this node has no default value and it will be
      considered 'required' (the ``required`` attribute will be True).

    - ``validator``: Optional validator for this node.  It should be
      an object that implements the
      :class:`colander.interfaces.Validator` interface.

    - ``title``: The title of this node.  Defaults to a captialization
      of the ``name``.  The title is used by higher-level systems (not
      by Colander itself).

    - ``description``: The description for this node.  Defaults to
      ``''`` (the emtpty string).  The description is used by
      higher-level systems (not by Colander itself).

    """
    
    _counter = itertools.count()
    
    def __new__(cls, *arg, **kw):
        inst = object.__new__(cls)
        inst._order = cls._counter.next()
        return inst
        
    def __init__(self, typ, *children, **kw):
        self.typ = typ
        self.validator = kw.get('validator', None)
        self.default = kw.get('default', _missing)
        self.name = kw.get('name', '')
        self.title = kw.get('title', self.name.capitalize())
        self.description = kw.get('description', '')
        self.children = list(children)

    def __repr__(self):
        return '<%s object at %x named %r>' % (self.__class__.__name__,
                                               id(self),
                                               self.name)

    @property
    def required(self):
        """ Property which returns true if this node is required in the
        schema """
        return self.default is _missing

    @property
    def sdefault(self):
        """ Return the *serialized* default of the node default or
        ``None`` if there is no default."""
        if self.default is _missing:
            return None
        return self.typ.serialize(self, self.default)

    def deserialize(self, value):
        """ Derialize the value based on the schema represented by this
        node """
        value = self.typ.deserialize(self, value)
        if self.validator is not None:
            self.validator(self, value)
        return value

    def serialize(self, value):
        """ Serialize the value based on the schema represented by this
        node """
        return self.typ.serialize(self, value)

    def add(self, node):
        """ Add a subnode to this node """
        self.children.append(node)

    def __getitem__(self, name):
        for node in self.children:
            if node.name == name:
                return node
        raise KeyError(name)

    def clone(self):
        """ Clone the schema node and return the clone.  All subnodes
        are also cloned recursively.  Attributes present in node
        dictionaries are preserved."""
        cloned = self.__class__(self.typ)
        cloned.__dict__.update(self.__dict__)
        cloned.children = [ node.clone() for node in self.children ]
        return cloned

class _SchemaMeta(type):
    def __init__(cls, name, bases, clsattrs):
        nodes = []
        for name, value in clsattrs.items():
            if isinstance(value, SchemaNode):
                value.name = name
                if not value.title:
                    value.title = name.capitalize()
                nodes.append((value._order, value))
        cls.__schema_nodes__ = nodes
        # Combine all attrs from this class and its subclasses.
        extended = []
        for c in cls.__mro__:
            extended.extend(getattr(c, '__schema_nodes__', []))
        # Sort the attrs to maintain the order as defined, and assign to the
        # class.
        extended.sort()
        cls.nodes = [x[1] for x in extended]

class Schema(object):
    schema_type = Mapping
    node_type = SchemaNode
    __metaclass__ = _SchemaMeta

    def __new__(cls, *args, **kw):
        node = object.__new__(cls.node_type)
        node.name = None
        node._order = SchemaNode._counter.next()
        typ = cls.schema_type(*args, **kw)
        node.__init__(typ)
        for n in cls.nodes:
            node.add(n)
        return node

MappingSchema = Schema

class SequenceSchema(Schema):
    schema_type = Sequence

class TupleSchema(Schema):
    schema_type = Tuple
