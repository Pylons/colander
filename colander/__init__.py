import datetime
import decimal
import itertools
import iso8601
import pprint
import re
import translationstring

_ = translationstring.TranslationStringFactory('colander')

class _missing(object):
    pass

def interpolate(msgs):
    for s in msgs:
        if hasattr(s, 'interpolate'):
            yield s.interpolate()
        else:
            yield s

class Invalid(Exception):
    """
    An exception raised by data types and validators indicating that
    the value for a particular node was not valid.

    The constructor receives a mandatory ``node`` argument.  This must
    be an instance of the :class:`colander.SchemaNode` class, or at
    least something with the same interface.

    The constructor also receives an optional ``msg`` keyword
    argument, defaulting to ``None``.  The ``msg`` argument is a
    freeform field indicating the error circumstance.

    The constructor additionally may receive a an optional ``value``
    keyword, indicating the value related to the error.
    """
    pos = None
    parent = None

    def __init__(self, node, msg=None, value=None):
        Exception.__init__(self, node, msg)
        self.node = node
        self.msg = msg
        self.value = value
        self.children = []

    def add(self, exc, pos=None):
        """ Add a child exception; ``exc`` must be an instance of
        :class:`colander.Invalid` or a subclass.

        ``pos`` is a value important for accurate error reporting.  If
        it is provided, it must be an integer representing the
        position of ``exc`` relative to all other subexceptions of
        this exception node.  For example, if the exception being
        added is about the third child of the exception which is
        ``self``, ``pos`` might be passed as ``3``.

        If ``pos`` is provided, it will be assigned to the ``pos``
        attribute of the provided ``exc`` object.

        The ``parent`` attribute of the provided ``exc`` will be set
        as a reference to ``self``.
        """
        exc.parent = self
        if pos is not None:
            exc.pos = pos
        self.children.append(exc)

    def __setitem__(self, name, msg):
        """ Add a subexception related to a child node with the
        message ``msg``. ``name`` must be present in the names of the
        set of child nodes of this exception's node; if this is not
        so, a :exc:`KeyError` is raised.

        For example, if the exception upon which ``__setitem__`` is
        called has a node attribute, and that node attribute has
        children that have the names ``name`` and ``title``, you may
        successfully call ``__setitem__('name', 'Bad name')`` or
        ``__setitem__('title', 'Bad title')``.  But calling
        ``__setitem__('wrong', 'whoops')`` will result in a
        :exc:`KeyError`.

        This method is typically only useful if the ``node`` attribute
        of the exception upon which it is called is a schema node
        representing a mapping.
        """
        for num, child in enumerate(self.node.children):
            if child.name == name:
                exc = Invalid(child, msg)
                self.add(exc, num)
                return
        raise KeyError(name)

    def paths(self):
        """ A generator which returns each path through the exception
        graph.  Each path is represented as a tuple of exception
        nodes.  Within each tuple, the leftmost item will represent
        the root schema node, the rightmost item will represent the
        leaf schema node."""
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
        """ Return a dictionary containing a basic
        (non-language-translated) error report for this exception"""
        paths = self.paths()
        errors = {}
        for path in paths:
            keyparts = []
            msgs = []
            for exc in path:
                exc.msg and msgs.append(exc.msg)
                keyname = exc._keyname()
                keyname and keyparts.append(keyname)
            errors['.'.join(keyparts)] = '; '.join(interpolate(msgs))
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

class Function(object):
    """ Validator which accepts a function and an optional message;
    the function is called with the ``value`` during validation.

    If the function returns anything falsy (``None``, ``False``, the
    empty string, ``0``, an object with a ``__nonzero__`` that returns
    ``False``, etc) when called during validation, an
    :exc:`colander.Invalid` exception is raised (validation fails);
    its msg will be the value of the ``message`` argument passed to
    this class' constructor.

    If the function returns a stringlike object (a ``str`` or
    ``unicode`` object) that is *not* the empty string , a
    :exc:`colander.Invalid` exception is raised using the stringlike
    value returned from the function as the exeption message
    (validation fails).

    If the function returns anything *except* a stringlike object
    object which is truthy (e.g. ``True``, the integer ``1``, an
    object with a ``__nonzero__`` that returns ``True``, etc), an
    :exc:`colander.Invalid` exception is *not* raised (validation
    succeeds).

    The default value for the ``message`` when not provided via the
    constructor is ``Invalid value``.
    """
    def __init__(self, function, message=_('Invalid value')):
        self.function = function
        self.message = message

    def __call__(self, node, value):
        result = self.function(value)
        if not result:
            raise Invalid(node, self.message)
        if isinstance(result, basestring):
            raise Invalid(node, result)

class Regex(object):
    """ Regular expression validator. Initialize it with the string 
        regular expression ``regex`` that will be compiled and matched 
        against ``value`` when validator is called. If ``msg`` is 
        supplied, it will be the error message to be used; otherwise, 
        defaults to 'String does not match expected pattern'.  
        
        When calling, if ``value`` matches the regular expression, 
        validation succeeds; otherwise, :exc:`colander.Invalid` is 
        raised with the ``msg`` error message. 
    """    
    def __init__(self, regex, msg=None):
        self.match_object = re.compile(regex)
        if msg is None:
            self.msg = _("String does not match expected pattern")
        else:
            self.msg = msg

    def __call__(self, node, value):
        if self.match_object.match(value) is None:
            raise Invalid(node, self.msg)

class Email(Regex):
    """ Email address validator. If ``msg`` is supplied, it will be 
        the error message to be used when raising :exc:`colander.Invalid`; 
        otherwise, defaults to 'Invalid email address'.  
    """    
    def __init__(self, msg=None):
        if msg is None:
            msg = _("Invalid email address")
        super(Email, self).__init__(
            u'(?i)^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$', msg=msg)

class Range(object):
    """ Validator which succeeds if the value it is passed is greater
    or equal to ``min`` and less than or equal to ``max``.  If ``min``
    is not specified, or is specified as ``None``, no lower bound
    exists.  If ``max`` is not specified, or is specified as ``None``,
    no upper bound exists.

    ``min_err`` is used to form the ``msg`` of the
    :exc:`colander.Invalid` error when reporting a validation failure
    caused by a value not meeting the minimum.  If ``min_err`` is
    specified, it must be a string.  The string may contain the
    replacement targets ``${min}`` and ``${val}``, representing the
    minimum value and the provided value respectively.  If it is not
    provided, it defaults to ``'${val} is less than minimum value
    ${min}'``.

    ``max_err`` is used to form the ``msg`` of the
    :exc:`colander.Invalid` error when reporting a validation failure
    caused by a value exceeding the maximum.  If ``max_err`` is
    specified, it must be a string.  The string may contain the
    replacement targets ``${max}`` and ``${val}``, representing the
    maximum value and the provided value respectively.  If it is not
    provided, it defaults to ``'${val} is greater than maximum value
    ${max}'``.
    """
    min_err = _('${val} is less than minimum value ${min}')
    max_err = _('${val} is greater than maximum value ${max}')

    def __init__(self, min=None, max=None, min_err=None, max_err=None):
        self.min = min
        self.max = max
        if min_err is not None:
            self.min_err = min_err
        if max_err is not None:
            self.max_err = max_err

    def __call__(self, node, value):
        if self.min is not None:
            if value < self.min:
                min_err = _(self.min_err, mapping={'val':value, 'min':self.min})
                raise Invalid(node, min_err)

        if self.max is not None:
            if value > self.max:
                max_err = _(self.max_err, mapping={'val':value, 'max':self.max})
                raise Invalid(node, max_err)

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
                min_err = _('Shorter than minimum length ${min}',
                            mapping={'min':self.min})
                raise Invalid(node, min_err)

        if self.max is not None:
            if len(value) > self.max:
                max_err = _('Longer than maximum length ${max}',
                            mapping={'max':self.max})
                raise Invalid(node, max_err)

class OneOf(object):
    """ Validator which succeeds if the value passed to it is one of
    a fixed set of values """
    def __init__(self, choices):
        self.choices = choices

    def __call__(self, node, value):
        if not value in self.choices:
            choices = ', '.join(['%s' % x for x in self.choices])
            err = _('"${val}" is not one of ${choices}',
                    mapping={'val':value, 'choices':choices})
            raise Invalid(node, err)

class Mapping(object):
    """ A type which represents a mapping of names to nodes.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type imply the named keys and values in the mapping.

    The constructor of this type accepts two extra optional keyword
    arguments that other types do not: ``unknown`` and ``partial``.
    Attributes of the same name can be set on a type instance to
    control the behavior after construction.

    unknown
        ``unknown`` controls the behavior of this type when an
        unknown key is encountered in the value passed to the
        ``deserialize`` method of this instance.  All the potential
        values of ``unknown`` are strings.  They are:

        - ``ignore`` means that keys that are not present in the schema
          associated with this type will be ignored during
          deserialization.

        - ``raise`` will cause a :exc:`colander.Invalid` exception to be
          raised when unknown keys are present during deserialization.

        - ``preserve`` will preserve the 'raw' unknown keys and values
          in the returned data structure during deserialization.

        Default: ``ignore``.

    partial
        ``partial`` controls the behavior of this type when a
        schema-expected key is missing from the value passed to the
        ``deserialize`` method of this instance.

        During deserialization, when ``partial`` is ``False``, a
        :exc:`colander.Invalid` exception will be raised if the
        mapping value does not contain a key specified by the schema
        node related to this mapping type.  When ``partial`` is
        ``True``, no exception is raised and a partial mapping will be
        deserialized.

        Default: ``False``.
    """

    def __init__(self, unknown='ignore', partial=False):
        self.unknown = unknown
        self.partial = partial

    def _set_unknown(self, value):
        if not value in ('ignore', 'raise', 'preserve'):
            raise ValueError(
                'unknown attribute must be one of "ignore", "raise", '
                'or "preserve"')
        self._unknown = value

    def _get_unknown(self):
        return self._unknown

    unknown = property(_get_unknown, _set_unknown)

    def _validate(self, node, value):
        try:
            return dict(value)
        except Exception, e:
            raise Invalid(node,
                          _('"${val}" is not a mapping type: ${err}',
                          mapping = {'val':value, 'err':e})
                          )

    def _impl(self, node, value, callback, default_callback, unknown=None,
              partial=None):
        if partial is None:
            partial = self.partial

        if unknown is None:
            unknown = self.unknown

        value = self._validate(node, value)

        error = None
        result = {}

        for num, subnode in enumerate(node.children):
            name = subnode.name
            subval = value.pop(name, _missing)

            try:
                if subval is _missing:
                    if subnode.required:
                        if not partial:
                            raise Invalid(
                                subnode,
                                _('"${val}" is required but missing',
                                  mapping={'val':subnode.name})
                                )
                        else:
                            continue
                    result[name] = default_callback(subnode)
                else:
                    result[name] = callback(subnode, subval)
            except Invalid, e:
                if error is None:
                    error = Invalid(node)
                error.add(e, num)

        if unknown == 'raise':
            if value:
                raise Invalid(
                    node,
                    _('Unrecognized keys in mapping: "${val}"',
                      mapping={'val':value})
                    )

        elif unknown == 'preserve':
            result.update(value)

        if error is not None:
            raise error
                
        return result

    def serialize(self, node, value):
        def callback(subnode, subval):
            return subnode.serialize(subval)
        def default_callback(subnode):
            return subnode.serialize(subnode.default)
        return self._impl(node, value, callback, default_callback,
                          unknown='ignore', partial=True)

    def deserialize(self, node, value):
        def callback(subnode, subval):
            return subnode.deserialize(subval)
        def default_callback(subnode):
            return subnode.default
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
            raise Invalid(
                node,
                _('"${val}" is not iterable', mapping={'val':value})
                )

        valuelen, nodelen = len(value), len(node.children)

        if valuelen != nodelen:
            raise Invalid(
                node,
                _('"${val}" has an incorrect number of elements '
                  '(expected ${exp}, was ${was})',
                  mapping={'val':value, 'exp':nodelen, 'was':valuelen})
                )

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
                error.add(e, num)
                
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
    indicates what should happen if the value found during serialization or
    deserialization does not have an ``__iter__`` method or is a
    mapping type.

    If ``accept_scalar`` is ``True`` and the value does not have an
    ``__iter__`` method or is a mapping type, the value will be turned
    into a single element list.

    If ``accept_scalar`` is ``False`` and the value does not have an
    ``__iter__`` method or is a mapping type, an
    :exc:`colander.Invalid` error will be raised during serialization
    and deserialization.

    The default value of ``accept_scalar`` is ``False``.
    """
    def __init__(self, accept_scalar=False):
        self.accept_scalar = accept_scalar

    def _validate(self, node, value, accept_scalar):
        if hasattr(value, '__iter__') and not hasattr(value, 'get'):
            return list(value)
        if accept_scalar:
            return [value]
        else:
            raise Invalid(node, _('"${val}" is not iterable',
                                  mapping={'val':value})
                          )

    def _impl(self, node, value, callback, accept_scalar):
        if accept_scalar is None:
            accept_scalar = self.accept_scalar
        value = self._validate(node, value, accept_scalar)

        error = None
        result = []
        for num, subval in enumerate(value):
            try:
                result.append(callback(node.children[0], subval))
            except Invalid, e:
                if error is None:
                    error = Invalid(node)
                error.add(e, num)
                
        if error is not None:
            raise error

        return result

    def deserialize(self, node, value, accept_scalar=None):
        """
        Along with the normal ``node`` and ``value`` arguments, this
        method accepts an additional optional keyword argument:
        ``accept_scalar``.  This keyword argument can be used to
        override the constructor value of the same name.

        If ``accept_scalar`` is ``True`` and the ``value`` does not
        have an ``__iter__`` method or is a mapping type, the value
        will be turned into a single element list.

        If ``accept_scalar`` is ``False`` and the value does not have an
        ``__iter__`` method or is a mapping type, an
        :exc:`colander.Invalid` error will be raised during serialization
        and deserialization.

        The default of ``accept_scalar`` is ``None``, which means
        respect the default ``accept_scalar`` value attached to this
        instance via its constructor.
        """
        def callback(subnode, subval):
            return subnode.deserialize(subval)
        return self._impl(node, value, callback, accept_scalar)

    def serialize(self, node, value, accept_scalar=None):
        """
        Along with the normal ``node`` and ``value`` arguments, this
        method accepts an additional optional keyword argument:
        ``accept_scalar``.  This keyword argument can be used to
        override the constructor value of the same name.

        If ``accept_scalar`` is ``True`` and the ``value`` does not
        have an ``__iter__`` method or is a mapping type, the value
        will be turned into a single element list.

        If ``accept_scalar`` is ``False`` and the value does not have an
        ``__iter__`` method or is a mapping type, an
        :exc:`colander.Invalid` error will be raised during serialization
        and deserialization.

        The default of ``accept_scalar`` is ``None``, which means
        respect the default ``accept_scalar`` value attached to this
        instance via its constructor.
        """
        def callback(subnode, subval):
            return subnode.serialize(subval)
        return self._impl(node, value, callback, accept_scalar)

Seq = Sequence

default_encoding = 'utf-8'

class String(object):
    """ A type representing a Unicode string.

    This type constructor accepts a number of arguments:

    ``encoding``
       Represents the encoding which should be applied to object
       serialization.  It defaults to ``utf-8`` if not provided.

    ``allow_empty``
       Boolean representing whether an empty string input to
       deserialize will be accepted even if the enclosing schema node
       is required (has no default).  Default: ``False``.

    Input to ``serialize`` is serialized to a Python ``str`` object,
    which is encoded in the encoding provided.

    If a string (as opposed to a unicode object) is provided as a
    value to either the serialize or deserialize method of this type,
    it must be encoded with the type's encoding; an
    :exc:`colander.Invalid` error will result if not.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type are ignored.
    """
    def __init__(self, encoding=None, allow_empty=False):
        if encoding is None:
            encoding = default_encoding
        self.encoding = encoding
        self.allow_empty = allow_empty
    
    def deserialize(self, node, value):
        try:
            if not isinstance(value, unicode):
                value = unicode(str(value), self.encoding)
        except Exception, e:
            raise Invalid(node,
                          _('${val} is not a string: %{err}',
                            mapping={'val':value, 'err':e}))
        if not value and not self.allow_empty:
            if node.required:
                raise Invalid(node, _('Required'))
            value = node.default
        return value

    def serialize(self, node, value):
        try:
            if isinstance(value, unicode):
                result = value.encode(self.encoding)
            else:
                # do validation here
                result = unicode(value, self.encoding).encode(self.encoding)
            return result
        except Exception, e:
            raise Invalid(node,
                          _('"${val} cannot be serialized to str: ${err}',
                            mapping={'val':value, 'err':e})
                          )

Str = String

class Number(object):
    """ Abstract base class for float, int, decimal """
    num = None
    def deserialize(self, node, value):
        try:
            return self.num(value)
        except Exception:
            if value == '':
                if node.required:
                    raise Invalid(node, _('Required'))
                return node.default
            raise Invalid(node,
                          _('"${val}" is not a number',
                            mapping={'val':value})
                          )

    def serialize(self, node, value):
        try:
            return str(self.num(value))
        except Exception:
            raise Invalid(node,
                          _('"${val}" is not a number',
                            mapping={'val':value}),
                          )

class Integer(Number):
    """ A type representing an integer.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type are ignored.
    """
    num = int
    
Int = Integer

class Float(Number):
    """ A type representing a float.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type are ignored.
    """
    num = float

class Decimal(Number):
    """ A type representing a decimal floating point.  Deserialization
    returns an instance of the Python ``decimal.Decimal`` type.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type are ignored.
    """
    def num(self, val):
        return decimal.Decimal(str(val))

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
            raise Invalid(node,
                          _('${val} is not a string', mapping={'val':value})
                          )
        if not value:
            if node.required:
                raise Invalid(node, _('Required'))
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
                    _('relative name "${val}" irresolveable without package',
                      mapping={'val':value})
                    )
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
                    _('relative name "${val}" irresolveable without package',
                      mapping={'val':value})
                    )
            name = module.split('.')
        else:
            name = value.split('.')
            if not name[0]:
                if module is None:
                    raise Invalid(
                        node,
                        _('relative name "${val}" irresolveable without '
                          'package', mapping={'val':value})
                        )
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
            raise Invalid(node,
                          _('"${val}" is not a string', mapping={'val':value}))
        try:
            if ':' in value:
                return self._pkg_resources_style(node, value)
            else:
                return self._zope_dottedname_style(node, value)
        except ImportError:
            raise Invalid(node,
                          _('The dotted name "${name}" cannot be imported',
                            mapping={'name':value}))

    def serialize(self, node, value):
        try:
            return value.__name__
        except AttributeError:
            raise Invalid(node,
                          _('"${val}" has no __name__',
                            mapping={'val':value})
                          )

class DateTime(object):
    """ A type representing a Python ``datetime.datetime`` object.

    This type serializes python ``datetime.datetime`` objects to a
    `ISO8601 <http://en.wikipedia.org/wiki/ISO_8601>`_ string format.
    The format includes the date, the time, and the timezone of the
    datetime.

    The constructor accepts an argument named ``default_tzinfo`` which
    should be a Python ``tzinfo`` object; by default it is None,
    meaning that the default tzinfo will be equivalent to UTC (Zulu
    time).  The ``default_tzinfo`` tzinfo object is used to convert
    'naive' datetimes to a timezone-aware representation during
    serialization.

    You can adjust the error message reported by this class by
    changing its ``err_template`` attribute in a subclass on an
    instance of this class.  By default, the ``err_template``
    attribute is the string ``${value} cannot be parsed as an iso8601
    date: ${exc}``.  This string is used as the interpolation subject
    of a dictionary composed of ``val`` and ``err``.  ``val`` and
    ``err`` are the unvalidatable value and the exception caused
    trying to convert the value, respectively.

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
    err_template =  _('${val} cannot be parsed as an iso8601 date: ${err}')
    def __init__(self, default_tzinfo=None):
        if default_tzinfo is None:
            default_tzinfo = iso8601.iso8601.Utc()
        self.default_tzinfo = default_tzinfo
        
    def serialize(self, node, value):
        if type(value) is datetime.date: # cant use isinstance; dt subs date
            value = datetime.datetime.combine(value, datetime.time())
        if not isinstance(value, datetime.datetime):
            raise Invalid(node,
                          _('"${val}" is not a datetime object',
                            mapping={'val':value})
                          )
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
                raise Invalid(node, _(self.err_template,
                                      mapping={'val':value, 'err':e}))
        return result

class Date(object):
    """ A type representing a Python ``datetime.date`` object.

    This type serializes python ``datetime.date`` objects to a
    `ISO8601 <http://en.wikipedia.org/wiki/ISO_8601>`_ string format.
    The format includes the date only.

    The constructor accepts no arguments.

    You can adjust the error message reported by this class by
    changing its ``err_template`` attribute in a subclass on an
    instance of this class.  By default, the ``err_template``
    attribute is the string ``${val} cannot be parsed as an iso8601
    date: ${err}``.  This string is used as the interpolation subject
    of a dictionary composed of ``val`` and ``err``.  ``val`` and
    ``exc`` are the unvalidatable value and the exception caused
    trying to convert the value, respectively.

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
    err_template =  _('${val} cannot be parsed as an iso8601 date: ${err}')
    def serialize(self, node, value):
        if isinstance(value, datetime.datetime):
            value = value.date()
        if not isinstance(value, datetime.date):
            raise Invalid(node,
                          _('"${val}" is not a date object',
                            mapping={'val':value})
                          )
        return value.isoformat()

    def deserialize(self, node, value):
        if not value:
            if node.required:
                raise Invalid(node, _('Required'))
            return node.default
        try:
            result = iso8601.parse_date(value)
            result = result.date()
        except (iso8601.ParseError, TypeError):
            try:
                year, month, day = map(int, value.split('-', 2))
                result = datetime.date(year, month, day)
            except Exception, e:
                raise Invalid(node,
                              _(self.err_template,
                                mapping={'val':value, 'err':e})
                              )
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
        """ Deserialize the value based on the schema represented by
        this node. """
        value = self.typ.deserialize(self, value)
        if self.validator is not None:
            self.validator(self, value)
        return value

    def serialize(self, value):
        """ Serialize the value based on the schema represented by
        this node."""
        return self.typ.serialize(self, value)

    def add(self, node):
        """ Add a subnode to this node. """
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
        typ = cls.schema_type()
        node.__init__(typ, *args, **kw)
        for n in cls.nodes:
            node.add(n)
        return node

MappingSchema = Schema

class SequenceSchema(object):
    schema_type = Sequence
    node_type = SchemaNode
    __metaclass__ = _SchemaMeta

    def __new__(cls, *args, **kw):
        node = object.__new__(cls.node_type)
        node.name = None
        node._order = SchemaNode._counter.next()
        typ = cls.schema_type()
        node.__init__(typ, *args, **kw)
        if not len(cls.nodes) == 1:
            raise Invalid(node,
                          'Sequence schemas must have exactly one child node')
        for n in cls.nodes:
            node.add(n)
        return node

class TupleSchema(Schema):
    schema_type = Tuple
