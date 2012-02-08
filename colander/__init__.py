import datetime
import decimal
import time
import itertools
import pprint
import re
import translationstring

from .compat import (
    text_,
    text_type,
    string_types,
    xrange,
    is_nonstr_iter,
    )

from . import iso8601

_ = translationstring.TranslationStringFactory('colander')

required = object()
_marker = required # bw compat

class _null(object):
    """ Represents a null value in colander-related operations. """
    def __nonzero__(self):
        return False

    # py3 compat
    __bool__ = __nonzero__

    def __repr__(self):
        return '<colander.null>'

    def __reduce__(self):
        return 'null' # when unpickled, refers to "null" below (singleton)

null = _null()

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

    The constructor additionally may receive an optional ``value``
    keyword, indicating the value related to the error.
    """
    pos = None
    positional = False

    def __init__(self, node, msg=None, value=None):
        Exception.__init__(self, node, msg)
        self.node = node
        self.msg = msg
        self.value = value
        self.children = []

    def messages(self):
        """ Return an iterable of error messages for this exception
        using the ``msg`` attribute of this error node.  If the
        ``msg`` attribute is iterable, it is returned.  If it is not
        iterable, a single-element list containing the ``msg`` value
        is returned."""
        if is_nonstr_iter(self.msg):
            return self.msg
        return [self.msg]

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
        """
        if self.node and isinstance(self.node.typ, Positional):
            exc.positional = True
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
        if self.positional:
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
            except Invalid as e:
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
        if isinstance(result, string_types):
            raise Invalid(node, result)

class Regex(object):
    """ Regular expression validator.

        Initialize it with the string regular expression ``regex``
        that will be compiled and matched against ``value`` when
        validator is called. If ``msg`` is supplied, it will be the
        error message to be used; otherwise, defaults to 'String does
        not match expected pattern'.

        The ``regex`` argument may also be a pattern object (the
        result of ``re.compile``) instead of a string.

        When calling, if ``value`` matches the regular expression,
        validation succeeds; otherwise, :exc:`colander.Invalid` is
        raised with the ``msg`` error message.
    """
    def __init__(self, regex, msg=None):
        if isinstance(regex, string_types):
            self.match_object = re.compile(regex)
        else:
            self.match_object = regex
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
            text_('(?i)^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$'), msg=msg)

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

class SchemaType(object):
    """ Base class for all schema types """
    def flatten(self, node, appstruct, prefix='', listitem=False):
        result = {}
        if listitem:
            selfname = prefix
        else:
            selfname = '%s%s' % (prefix, node.name)
        result[selfname] = appstruct
        return result

    def unflatten(self, node, paths, fstruct):
        name = node.name
        assert paths == [name], "paths should be [name] for leaf nodes."
        return fstruct[name]

    def set_value(self, node, appstruct, path, value):
        raise AssertionError("Can't call 'set_value' on a leaf node.")

    def get_value(self, node, appstruct, path):
        raise AssertionError("Can't call 'set_value' on a leaf node.")

class Mapping(SchemaType):
    """ A type which represents a mapping of names to nodes.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type imply the named keys and values in the mapping.

    The constructor of this type accepts one extra optional keyword
    argument that other types do not: ``unknown``.  An attribute of
    the same name can be set on a type instance to control the
    behavior after construction.

    unknown
        ``unknown`` controls the behavior of this type when an unknown
        key is encountered in the cstruct passed to the
        ``deserialize`` method of this instance.  All the potential
        values of ``unknown`` are strings.  They are:

        - ``ignore`` means that keys that are not present in the schema
          associated with this type will be ignored during
          deserialization.

        - ``raise`` will cause a :exc:`colander.Invalid` exception to
          be raised when unknown keys are present in the cstruct
          during deserialization.

        - ``preserve`` will preserve the 'raw' unknown keys and values
          in the appstruct returned by deserialization.

        Default: ``ignore``.

    Special behavior is exhibited when a subvalue of a mapping is
    present in the schema but is missing from the mapping passed to
    either the ``serialize`` or ``deserialize`` method of this class.
    In this case, the :attr:`colander.null` value will be passed to
    the ``serialize`` or ``deserialize`` method of the schema node
    representing the subvalue of the mapping respectively.  During
    serialization, this will result in the behavior described in
    :ref:`serializing_null` for the subnode.  During deserialization,
    this will result in the behavior described in
    :ref:`deserializing_null` for the subnode.

    If the :attr:`colander.null` value is passed to the serialize
    method of this class, a dictionary will be returned, where each of
    the values in the returned dictionary is the serialized
    representation of the null value for its type.
    """
    def __init__(self, unknown='ignore'):
        self.unknown = unknown

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
        except Exception as e:
            raise Invalid(node,
                          _('"${val}" is not a mapping type: ${err}',
                          mapping = {'val':value, 'err':e})
                          )

    def _impl(self, node, value, callback):
        value = self._validate(node, value)

        error = None
        result = {}

        for num, subnode in enumerate(node.children):
            name = subnode.name
            subval = value.pop(name, null)
            try:
                result[name] = callback(subnode, subval)
            except Invalid as e:
                if error is None:
                    error = Invalid(node)
                error.add(e, num)

        if self.unknown == 'raise':
            if value:
                raise Invalid(
                    node,
                    _('Unrecognized keys in mapping: "${val}"',
                      mapping={'val':value})
                    )

        elif self.unknown == 'preserve':
            result.update(value)

        if error is not None:
            raise error

        return result

    def serialize(self, node, appstruct):
        if appstruct is null:
            appstruct = {}

        def callback(subnode, subappstruct):
            return subnode.serialize(subappstruct)

        return self._impl(node, appstruct, callback)

    def deserialize(self, node, cstruct):
        if cstruct is null:
            return null

        def callback(subnode, subcstruct):
            return subnode.deserialize(subcstruct)

        return self._impl(node, cstruct, callback)

    def flatten(self, node, appstruct, prefix='', listitem=False):
        result = {}
        if listitem:
            selfprefix = prefix
        else:
            selfprefix = '%s%s.' % (prefix, node.name)

        for subnode in node.children:
            name = subnode.name
            substruct = appstruct.get(name, null)
            result.update(subnode.typ.flatten(subnode, substruct,
                                              prefix=selfprefix))
        return result

    def unflatten(self, node, paths, fstruct):
        return _unflatten_mapping(node, paths, fstruct)

    def set_value(self, node, appstruct, path, value):
        if '.' in path:
            next_name, rest = path.split('.', 1)
            next_node = node[next_name]
            next_appstruct = appstruct[next_name]
            appstruct[next_name] = next_node.typ.set_value(
                next_node, next_appstruct, rest, value)
        else:
            appstruct[path] = value
        return appstruct

    def get_value(self, node, appstruct, path):
        if '.' in path:
            name, rest = path.split('.', 1)
            next_node = node[name]
            return next_node.typ.get_value(next_node, appstruct[name], rest)
        return appstruct[path]


class Positional(object):
    """
    Marker abstract base class meaning 'this type has children which
    should be addressed by position instead of name' (e.g. via seq[0],
    but never seq['name']).  This is consulted by Invalid.asdict when
    creating a dictionary representation of an error tree.
    """

class Tuple(Positional, SchemaType):
    """ A type which represents a fixed-length sequence of nodes.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type imply the positional elements of the tuple in the order
    they are added.

    This type is willing to serialize and deserialized iterables that,
    when converted to a tuple, have the same number of elements as the
    number of the associated node's subnodes.

    If the :attr:`colander.null` value is passed to the serialize
    method of this class, the :attr:`colander.null` value will be
    returned.
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
            except Invalid as e:
                if error is None:
                    error = Invalid(node)
                error.add(e, num)

        if error is not None:
            raise error

        return tuple(result)

    def serialize(self, node, appstruct):
        if appstruct is null:
            return null

        def callback(subnode, subappstruct):
            return subnode.serialize(subappstruct)

        return self._impl(node, appstruct, callback)

    def deserialize(self, node, cstruct):
        if cstruct is null:
            return null

        def callback(subnode, subval):
            return subnode.deserialize(subval)

        return self._impl(node, cstruct, callback)

    def flatten(self, node, appstruct, prefix='', listitem=False):
        result = {}
        if listitem:
            selfprefix = prefix
        else:
            selfprefix = '%s%s.' % (prefix, node.name)

        for num, subnode in enumerate(node.children):
            substruct = appstruct[num]
            result.update(subnode.typ.flatten(subnode, substruct,
                                              prefix=selfprefix))
        return result

    def unflatten(self, node, paths, fstruct):
        mapstruct = _unflatten_mapping(node, paths, fstruct)
        appstruct = []
        for subnode in node.children:
            appstruct.append(mapstruct[subnode.name])
        return tuple(appstruct)

    def set_value(self, node, appstruct, path, value):
        appstruct = list(appstruct)
        if '.' in path:
            next_name, rest = path.split('.', 1)
        else:
            next_name, rest = path, None
        for index, next_node in enumerate(node.children):
            if next_node.name == next_name:
                break
        else:
            raise KeyError(next_name)
        if rest is not None:
            next_appstruct = appstruct[index]
            appstruct[index] = next_node.typ.set_value(
                next_node, next_appstruct, rest, value)
        else:
            appstruct[index] = value
        return tuple(appstruct)

    def get_value(self, node, appstruct, path):
        if '.' in path:
            name, rest = path.split('.', 1)
        else:
            name, rest = path, None
        for index, next_node in enumerate(node.children):
            if next_node.name == name:
                break
        else:
            raise KeyError(name)
        if rest is not None:
            return next_node.typ.get_value(next_node, appstruct[index], rest)
        return appstruct[index]


class Sequence(Positional, SchemaType):
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

    If the :attr:`colander.null` value is passed to the serialize
    method of this class, the :attr:`colander.null` value is returned.
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
            except Invalid as e:
                if error is None:
                    error = Invalid(node)
                error.add(e, num)

        if error is not None:
            raise error

        return result

    def serialize(self, node, appstruct, accept_scalar=None):
        """
        Along with the normal ``node`` and ``appstruct`` arguments,
        this method accepts an additional optional keyword argument:
        ``accept_scalar``.  This keyword argument can be used to
        override the constructor value of the same name.

        If ``accept_scalar`` is ``True`` and the ``appstruct`` does
        not have an ``__iter__`` method or is a mapping type, the
        value will be turned into a single element list.

        If ``accept_scalar`` is ``False`` and the ``appstruct`` does
        not have an ``__iter__`` method or is a mapping type, an
        :exc:`colander.Invalid` error will be raised during
        serialization and deserialization.

        The default of ``accept_scalar`` is ``None``, which means
        respect the default ``accept_scalar`` value attached to this
        instance via its constructor.
        """
        if appstruct is null:
            return null

        def callback(subnode, subappstruct):
            return subnode.serialize(subappstruct)

        return self._impl(node, appstruct, callback, accept_scalar)

    def deserialize(self, node, cstruct, accept_scalar=None):
        """
        Along with the normal ``node`` and ``cstruct`` arguments, this
        method accepts an additional optional keyword argument:
        ``accept_scalar``.  This keyword argument can be used to
        override the constructor value of the same name.

        If ``accept_scalar`` is ``True`` and the ``cstruct`` does not
        have an ``__iter__`` method or is a mapping type, the value
        will be turned into a single element list.

        If ``accept_scalar`` is ``False`` and the ``cstruct`` does not have an
        ``__iter__`` method or is a mapping type, an
        :exc:`colander.Invalid` error will be raised during serialization
        and deserialization.

        The default of ``accept_scalar`` is ``None``, which means
        respect the default ``accept_scalar`` value attached to this
        instance via its constructor.
        """
        if cstruct is null:
            return null

        def callback(subnode, subcstruct):
            return subnode.deserialize(subcstruct)

        return self._impl(node, cstruct, callback, accept_scalar)

    def flatten(self, node, appstruct, prefix='', listitem=False):
        result = {}
        if listitem:
            selfprefix = prefix
        else:
            selfprefix = '%s%s.' % (prefix, node.name)

        childnode = node.children[0]

        for num, subval in enumerate(appstruct):
            subname = '%s%s' % (selfprefix, num)
            subprefix = subname + '.'
            result.update(childnode.typ.flatten(
                childnode, subval, prefix=subprefix, listitem=True))

        return result

    def unflatten(self, node, paths, fstruct):
        only_child = node.children[0]
        child_name = only_child.name
        def get_child(name):
            return only_child
        def rewrite_subpath(subpath):
            if '.' in subpath:
                suffix = subpath.split('.', 1)[1]
                return '%s.%s' % (child_name, suffix)
            return child_name
        mapstruct = _unflatten_mapping(node, paths, fstruct,
                                       get_child, rewrite_subpath)
        return [mapstruct[str(index)] for index in xrange(len(mapstruct))]

    def set_value(self, node, appstruct, path, value):
        if '.' in path:
            next_name, rest = path.split('.', 1)
            index = int(next_name)
            next_node = node.children[0]
            next_appstruct = appstruct[index]
            appstruct[index] = next_node.typ.set_value(
                next_node, next_appstruct, rest, value)
        else:
            index = int(path)
            appstruct[index] = value
        return appstruct

    def get_value(self, node, appstruct, path):
        if '.' in path:
            name, rest = path.split('.', 1)
            index = int(name)
            next_node = node.children[0]
            return next_node.typ.get_value(next_node, appstruct[index], rest)
        return appstruct[int(path)]

Seq = Sequence

class String(SchemaType):
    """ A type representing a Unicode string.

    This type constructor accepts one argument:

    ``encoding``
       Represents the encoding which should be applied to value
       serialization and deserialization, for example ``utf-8``.  If
       ``encoding`` is passed as ``None``, the ``serialize`` method of
       this type will not do any special encoding of the appstruct it is
       provided, nor will the ``deserialize`` method of this type do
       any special decoding of the cstruct it is provided; inputs and
       outputs will be assumed to be Unicode.  ``encoding`` defaults
       to ``None``.

       If ``encoding`` is ``None``:

       - A Unicode input value to ``serialize`` is returned untouched.

       - A non-Unicode input value to ``serialize`` is run through the
         ``unicode()`` function without an ``encoding`` parameter
         (``unicode(value)``) and the result is returned.

       - A Unicode input value to ``deserialize`` is returned untouched.

       - A non-Unicode input value to ``deserialize`` is run through the
         ``unicode()`` function without an ``encoding`` parameter
         (``unicode(value)``) and the result is returned.

       If ``encoding`` is not ``None``:

       - A Unicode input value to ``serialize`` is run through the
         ``unicode`` function with the encoding parameter
         (``unicode(value, encoding)``) and the result (a ``str``
         object) is returned.

       - A non-Unicode input value to ``serialize`` is converted to a
         Unicode using the encoding (``unicode(value, encoding)``);
         subsequently the Unicode object is reeencoded to a ``str``
         object using the encoding and returned.

       - A Unicode input value to ``deserialize`` is returned
         untouched.

       - A non-Unicode input value to ``deserialize`` is converted to
         a ``str`` object using ``str(value``).  The resulting str
         value is converted to Unicode using the encoding
         (``unicode(value, encoding)``) and the result is returned.

       A corollary: If a string (as opposed to a unicode object) is
       provided as a value to either the serialize or deserialize
       method of this type, and the type also has an non-None
       ``encoding``, the string must be encoded with the type's
       encoding.  If this is not true, an :exc:`colander.Invalid`
       error will result.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type are ignored.
    """
    def __init__(self, encoding=None):
        self.encoding = encoding

    def serialize(self, node, appstruct):
        if appstruct is null:
            return null

        try:
            if isinstance(appstruct, (text_type, bytes)):
                encoding = self.encoding
                if encoding:
                    result = text_(appstruct, encoding).encode(encoding)
                else:
                    result = text_type(appstruct)
            else:
                result = text_type(appstruct)
            return result
        except Exception as e:
            raise Invalid(node,
                          _('"${val} cannot be serialized: ${err}',
                            mapping={'val':appstruct, 'err':e})
                          )
    def deserialize(self, node, cstruct):
        if not cstruct:
            return null

        try:
            result = cstruct
            if isinstance(result, (text_type, bytes)):
                if self.encoding:
                    result = text_(cstruct, self.encoding)
                else:
                    result = text_type(cstruct)
            else:
                result = text_type(cstruct)
        except Exception as e:
            raise Invalid(node,
                          _('${val} is not a string: %{err}',
                            mapping={'val':cstruct, 'err':e}))

        return result

Str = String

class Number(SchemaType):
    """ Abstract base class for float, int, decimal """

    num = None

    def serialize(self, node, appstruct):
        if appstruct is null:
            return null

        try:
            return str(self.num(appstruct))
        except Exception:
            raise Invalid(node,
                          _('"${val}" is not a number',
                            mapping={'val':appstruct}),
                          )
    def deserialize(self, node, cstruct):
        if cstruct != 0 and not cstruct:
            return null

        try:
            return self.num(cstruct)
        except Exception:
            raise Invalid(node,
                          _('"${val}" is not a number',
                            mapping={'val':cstruct})
                          )

class Integer(Number):
    """ A type representing an integer.

    If the :attr:`colander.null` value is passed to the serialize
    method of this class, the :attr:`colander.null` value will be
    returned.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type are ignored.
    """
    num = int

Int = Integer

class Float(Number):
    """ A type representing a float.

    If the :attr:`colander.null` value is passed to the serialize
    method of this class, the :attr:`colander.null` value will be
    returned.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type are ignored.
    """
    num = float

class Decimal(Number):
    """ A type representing a decimal floating point.  Deserialization
    returns an instance of the Python ``decimal.Decimal`` type.

    If the :attr:`colander.null` value is passed to the serialize
    method of this class, the :attr:`colander.null` value will be
    returned.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type are ignored.
    """
    def num(self, val):
        return decimal.Decimal(str(val))

class Boolean(SchemaType):
    """ A type representing a boolean object.

    During deserialization, a value in the set (``false``, ``0``) will
    be considered ``False``.  Anything else is considered
    ``True``. Case is ignored.

    Serialization will produce ``true`` or ``false`` based on the
    value.

    If the :attr:`colander.null` value is passed to the serialize
    method of this class, the :attr:`colander.null` value will be
    returned.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type are ignored.
    """

    def serialize(self, node, appstruct):
        if appstruct is null:
            return null

        return appstruct and 'true' or 'false'

    def deserialize(self, node, cstruct):
        if cstruct is null:
            return null

        try:
            result = str(cstruct)
        except:
            raise Invalid(node,
                          _('${val} is not a string', mapping={'val':cstruct})
                          )
        result = result.lower()

        if result in ('false', '0'):
            return False

        return True

Bool = Boolean

class GlobalObject(SchemaType):
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

    If the :attr:`colander.null` value is passed to the serialize
    method of this class, the :attr:`colander.null` value will be
    returned.

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
            except AttributeError: # pragma: no cover
                __import__(used)
                found = getattr(found, n)

        return found

    def serialize(self, node, appstruct):
        if appstruct is null:
            return null

        try:
            return appstruct.__name__
        except AttributeError:
            raise Invalid(node,
                          _('"${val}" has no __name__',
                            mapping={'val':appstruct})
                          )
    def deserialize(self, node, cstruct):
        if not cstruct:
            return null

        if not isinstance(cstruct, string_types):
            raise Invalid(node,
                          _('"${val}" is not a string',
                            mapping={'val':cstruct}))
        try:
            if ':' in cstruct:
                return self._pkg_resources_style(node, cstruct)
            else:
                return self._zope_dottedname_style(node, cstruct)
        except ImportError:
            raise Invalid(node,
                          _('The dotted name "${name}" cannot be imported',
                            mapping={'name':cstruct}))

class DateTime(SchemaType):
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
    attribute is the string ``Invalid date``.  This string is used as
    the interpolation subject of a dictionary composed of ``val`` and
    ``err``.  ``val`` and ``err`` are the unvalidatable value and the
    exception caused trying to convert the value, respectively. These
    may be used in an overridden err_template as ``${val}`` and
    ``${err}`` respectively as necessary, e.g. ``_('${val} cannot be
    parsed as an iso8601 date: ${err}')``.

    For convenience, this type is also willing to coerce
    ``datetime.date`` objects to a DateTime ISO string representation
    during serialization.  It does so by using midnight of the day as
    the time, and uses the ``default_tzinfo`` to give the
    serialization a timezone.

    Likewise, for convenience, during deserialization, this type will
    convert ``YYYY-MM-DD`` ISO8601 values to a datetime object.  It
    does so by using midnight of the day as the time, and uses the
    ``default_tzinfo`` to give the serialization a timezone.

    If the :attr:`colander.null` value is passed to the serialize
    method of this class, the :attr:`colander.null` value will be
    returned.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type are ignored.
    """
    err_template =  _('Invalid date')

    def __init__(self, default_tzinfo=_marker):
        if default_tzinfo is _marker:
            default_tzinfo = iso8601.Utc()
        self.default_tzinfo = default_tzinfo

    def serialize(self, node, appstruct):
        if appstruct is null:
            return null

        if type(appstruct) is datetime.date: # cant use isinstance; dt subs date
            appstruct = datetime.datetime.combine(appstruct, datetime.time())

        if not isinstance(appstruct, datetime.datetime):
            raise Invalid(node,
                          _('"${val}" is not a datetime object',
                            mapping={'val':appstruct})
                          )

        if appstruct.tzinfo is None:
            appstruct = appstruct.replace(tzinfo=self.default_tzinfo)
        return appstruct.isoformat()

    def deserialize(self, node, cstruct):
        if not cstruct:
            return null

        try:
            result = iso8601.parse_date(
                cstruct, default_timezone=self.default_tzinfo)
        except (iso8601.ParseError, TypeError) as e:
            try:
                year, month, day = map(int, cstruct.split('-', 2))
                result = datetime.datetime(year, month, day,
                                           tzinfo=self.default_tzinfo)
            except Exception as e:
                raise Invalid(node, _(self.err_template,
                                      mapping={'val':cstruct, 'err':e}))
        return result

class Date(SchemaType):
    """ A type representing a Python ``datetime.date`` object.

    This type serializes python ``datetime.date`` objects to a
    `ISO8601 <http://en.wikipedia.org/wiki/ISO_8601>`_ string format.
    The format includes the date only.

    The constructor accepts no arguments.

    You can adjust the error message reported by this class by
    changing its ``err_template`` attribute in a subclass on an
    instance of this class.  By default, the ``err_template``
    attribute is the string ``Invalid date``.  This string is used as
    the interpolation subject of a dictionary composed of ``val`` and
    ``err``.  ``val`` and ``err`` are the unvalidatable value and the
    exception caused trying to convert the value, respectively. These
    may be used in an overridden err_template as ``${val}`` and
    ``${err}`` respectively as necessary, e.g. ``_('${val} cannot be
    parsed as an iso8601 date: ${err}')``.

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

    If the :attr:`colander.null` value is passed to the serialize
    method of this class, the :attr:`colander.null` value will be
    returned.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type are ignored.
    """

    err_template =  _('Invalid date')

    def serialize(self, node, appstruct):
        if appstruct is null:
            return null

        if isinstance(appstruct, datetime.datetime):
            appstruct = appstruct.date()

        if not isinstance(appstruct, datetime.date):
            raise Invalid(node,
                          _('"${val}" is not a date object',
                            mapping={'val':appstruct})
                          )

        return appstruct.isoformat()

    def deserialize(self, node, cstruct):
        if not cstruct:
            return null
        try:
            result = iso8601.parse_date(cstruct)
            result = result.date()
        except (iso8601.ParseError, TypeError):
            try:
                year, month, day = map(int, cstruct.split('-', 2))
                result = datetime.date(year, month, day)
            except Exception as e:
                raise Invalid(node,
                              _(self.err_template,
                                mapping={'val':cstruct, 'err':e})
                              )
        return result

class Time(SchemaType):
    """ A type representing a Python ``datetime.time`` object.

    .. note:: This type is new as of Colander 0.9.3.

    This type serializes python ``datetime.time`` objects to a
    `ISO8601 <http://en.wikipedia.org/wiki/ISO_8601>`_ string format.
    The format includes the date only.

    The constructor accepts no arguments.

    You can adjust the error message reported by this class by
    changing its ``err_template`` attribute in a subclass on an
    instance of this class.  By default, the ``err_template``
    attribute is the string ``Invalid date``.  This string is used as
    the interpolation subject of a dictionary composed of ``val`` and
    ``err``.  ``val`` and ``err`` are the unvalidatable value and the
    exception caused trying to convert the value, respectively. These
    may be used in an overridden err_template as ``${val}`` and
    ``${err}`` respectively as necessary, e.g. ``_('${val} cannot be
    parsed as an iso8601 date: ${err}')``.

    For convenience, this type is also willing to coerce
    ``datetime.datetime`` objects to a time-only ISO string
    representation during serialization.  It does so by stripping off
    any date information, converting the ``datetime.datetime`` into a
    time before serializing.

    Likewise, for convenience, this type is also willing to coerce ISO
    representations that contain time info into a ``datetime.time``
    object during deserialization.  It does so by throwing away any
    date information related to the serialized value during
    deserialization.

    If the :attr:`colander.null` value is passed to the serialize
    method of this class, the :attr:`colander.null` value will be
    returned.

    The subnodes of the :class:`colander.SchemaNode` that wraps
    this type are ignored.
    """

    err_template =  _('Invalid time')

    def serialize(self, node, appstruct):
        if appstruct is null:
            return null

        if isinstance(appstruct, datetime.datetime):
            appstruct = appstruct.time()

        if not isinstance(appstruct, datetime.time):
            raise Invalid(node,
                          _('"${val}" is not a time object',
                            mapping={'val':appstruct})
                          )

        return appstruct.isoformat().split('.')[0]

    def deserialize(self, node, cstruct):
        if not cstruct:
            return null
        try:
            result = iso8601.parse_date(cstruct)
            result = result.time()
        except (iso8601.ParseError, TypeError):
            try:
                result = timeparse(cstruct, '%H:%M:%S')
            except ValueError:
                try:
                    result = timeparse(cstruct, '%H:%M')
                except Exception as e:
                    raise Invalid(node,
                                  _(self.err_template,
                                    mapping={'val':cstruct, 'err':e})
                                  )
        return result

def timeparse(t, format):
    return datetime.datetime(*time.strptime(t, format)[0:6]).time()

class SchemaNode(object):
    """
    Fundamental building block of schemas.

    The constructor accepts these positional arguments:

    - ``typ`` (required): The 'type' for this node.  It should be an
      instance of a class that implements the
      :class:`colander.interfaces.Type` interface.

    - ``children``: a sequence of subnodes.  If the subnodes of this
      node are not known at construction time, they can later be added
      via the ``add`` method.

    The constructor accepts these keyword arguments:

    - ``name``: The name of this node.

    - ``default``: The default serialization value for this node.
      Default: :attr:`colander.null`.

    - ``missing``: The default deserialization value for this node.  If it is
      not provided, the missing value of this node will be the special marker
      value :attr:`colander.required`, indicating that it is considered
      'required'.  When ``missing`` is :attr:`colander.required`, the
      ``required`` computed attribute will be ``True``.

    - ``preparer``: Optional preparer for this node.  It should be
      an object that implements the
      :class:`colander.interfaces.Preparer` interface.

    - ``validator``: Optional validator for this node.  It should be
      an object that implements the
      :class:`colander.interfaces.Validator` interface.

    - ``after_bind``: A callback which is called after a clone of this
      node has 'bound' all of its values successfully. This callback
      is useful for performing arbitrary actions to the cloned node,
      or direct children of the cloned node (such as removing or
      adding children) at bind time.  A 'binding' is the result of an
      execution of the ``bind`` method of the clone's prototype node,
      or one of the parents of the clone's prototype nodes.  The
      deepest nodes in the node tree are bound first, so the
      ``after_bind`` methods of the deepest nodes are called before
      the shallowest.  The ``after_bind`` callback should should
      accept two values: ``node`` and ``kw``.  ``node`` will be a
      clone of the bound node object, ``kw`` will be the set of
      keywords passed to the ``bind`` method.

    - ``title``: The title of this node.  Defaults to a titleization
      of the ``name`` (underscores replaced with empty strings and the
      first letter of every resulting word capitalized).  The title is
      used by higher-level systems (not by Colander itself).

    - ``description``: The description for this node.  Defaults to
      ``''`` (the empty string).  The description is used by
      higher-level systems (not by Colander itself).

    - ``widget``: The 'widget' for this node.  Defaults to ``None``.
      The widget attribute is not interpreted by Colander itself, it
      is only meaningful to higher-level systems such as Deform.

    Arbitrary keyword arguments remaining will be attached to the node
    object unmolested.
    """

    _counter = itertools.count()

    def __new__(cls, *arg, **kw):
        inst = object.__new__(cls)
        inst._order = next(cls._counter)
        return inst

    def __init__(self, typ, *children, **kw):
        self.typ = typ
        self.preparer = kw.pop('preparer', None)
        self.validator = kw.pop('validator', None)
        self.default = kw.pop('default', null)
        self.missing = kw.pop('missing', required)
        self.name = kw.pop('name', '')
        self.raw_title = kw.pop('title', _marker)
        if self.raw_title is _marker:
            self.title = self.name.replace('_', ' ').title()
        else:
            self.title = self.raw_title
        self.description = kw.pop('description', '')
        self.widget = kw.pop('widget', None)
        self.after_bind = kw.pop('after_bind', None)
        self.__dict__.update(kw)
        self.children = list(children)

    @property
    def required(self):
        """ A property which returns ``True`` if the ``missing`` value
        related to this node was not specified.

        A return value of ``True`` implies that a ``missing`` value wasn't
        specified for this node or that the ``missing`` value of this node is
        :attr:`colander.required`.  A return value of ``False`` implies that
        a 'real' ``missing`` value was specified for this node."""
        if isinstance(self.missing, deferred):  # unbound schema with deferreds
            return True
        return self.missing is required

    def serialize(self, appstruct=null):
        """ Serialize the :term:`appstruct` to a :term:`cstruct` based
        on the schema represented by this node and return the
        cstruct.

        If ``appstruct`` is :attr:`colander.null`, return the
        serialized value of this node's ``default`` attribute (by
        default, the serialization of :attr:`colander.null`).

        If an ``appstruct`` argument is not explicitly provided, it
        defaults to :attr:`colander.null`.
        """
        if appstruct is null:
            appstruct = self.default
        if isinstance(appstruct, deferred): # unbound schema with deferreds
            appstruct = null
        cstruct = self.typ.serialize(self, appstruct)
        return cstruct

    def flatten(self, appstruct):
        """ Create and return a data structure which is a flattened
        representation of the passed in struct based on the schema represented
        by this node.  The return data structure is a dictionary; its keys are
        dotted names.  Each dotted name represents a path to a location in the
        schema.  The values of of the flattened dictionary are subvalues of
        the passed in struct."""
        flat = self.typ.flatten(self, appstruct)
        return flat

    def unflatten(self, fstruct):
        """ Create and return a data structure with nested substructures based
        on the schema represented by this node using the flattened
        representation passed in. This is the inverse operation to
        :meth:`colander.SchemaNode.flatten`."""
        paths = sorted(fstruct.keys())
        return self.typ.unflatten(self, paths, fstruct)

    def set_value(self, appstruct, dotted_name, value):
        """ Uses the schema to set a value in a nested datastructure from a
        dotted name path. """
        self.typ.set_value(self, appstruct, dotted_name, value)

    def get_value(self, appstruct, dotted_name):
        """ Traverses the nested data structure using the schema and retrieves
        the value specified by the dotted name path."""
        return self.typ.get_value(self, appstruct, dotted_name)

    def deserialize(self, cstruct=null):
        """ Deserialize the :term:`cstruct` into an :term:`appstruct` based
        on the schema, run this :term:`appstruct` through the
        preparer, if one is present, then validate the
        prepared appstruct.  The ``cstruct`` value is deserialized into an
        ``appstruct`` unconditionally.

        If ``appstruct`` returned by type deserialization and
        preparation is the value :attr:`colander.null`, do something
        special before attempting validation:

        - If the ``missing`` attribute of this node has been set explicitly,
          return its value.  No validation of this value is performed; it is
          simply returned.

        - If the ``missing`` attribute of this node has not been set
          explicitly, raise a :exc:`colander.Invalid` exception error.

        If the appstruct is not ``colander.null`` and cannot be validated , a
        :exc:`colander.Invalid` exception will be raised.

        If a ``cstruct`` argument is not explicitly provided, it
        defaults to :attr:`colander.null`.
        """
        appstruct = self.typ.deserialize(self, cstruct)

        if self.preparer is not None:
            appstruct = self.preparer(appstruct)

        if appstruct is null:
            appstruct = self.missing
            if appstruct is required:
                raise Invalid(self, _('Required'))
            if isinstance(appstruct, deferred): # unbound schema with deferreds
                raise Invalid(self, _('Required'))
            # We never deserialize or validate the missing value
            return appstruct

        if self.validator is not None:
            if not isinstance(self.validator, deferred): # unbound
                self.validator(self, appstruct)
        return appstruct

    def add(self, node):
        """ Add a subnode to this node. """
        self.children.append(node)

    def clone(self):
        """ Clone the schema node and return the clone.  All subnodes
        are also cloned recursively.  Attributes present in node
        dictionaries are preserved."""
        cloned = self.__class__(self.typ)
        cloned.__dict__.update(self.__dict__)
        cloned.children = [ node.clone() for node in self.children ]
        return cloned

    def bind(self, **kw):
        """ Resolve any deferred values attached to this schema node
        and its children (recursively), using the keywords passed as
        ``kw`` as input to each deferred value.  This function
        *clones* the schema it is called upon and returns the cloned
        value.  The original schema node (the source of the clone)
        is not modified."""
        cloned = self.clone()
        cloned._bind(kw)
        return cloned

    def _bind(self, kw):
        for child in self.children:
            child._bind(kw)
        for k, v in self.__dict__.items():
            if isinstance(v, deferred):
                v = v(self, kw)
                setattr(self, k, v)
        if getattr(self, 'after_bind', None):
            self.after_bind(self, kw)

    def __delitem__(self, name):
        """ Remove a subnode by name """
        for idx, node in enumerate(self.children[:]):
            if node.name == name:
                return self.children.pop(idx)
        raise KeyError(name)

    def __getitem__(self, name):
        """ Get a subnode by name. """
        for node in self.children:
            if node.name == name:
                return node
        raise KeyError(name)

    def __setitem__(self, name, newnode):
        """ Replace a subnode by name """
        for idx, node in enumerate(self.children[:]):
            if node.name == name:
                self.children[idx] = newnode
                newnode.name = name
                return node
        raise KeyError(name)

    def __iter__(self):
        """ Iterate over the children nodes of this schema node """
        return iter(self.children)

    def __contains__(self, name):
        try:
            self[name]
        except KeyError:
            return False
        return True

    def __repr__(self):
        return '<%s.%s object at %d (named %s)>' % (
            self.__module__,
            self.__class__.__name__,
            id(self),
            self.name,
            )

class _SchemaMeta(type):
    def __init__(cls, name, bases, clsattrs):
        nodes = []
        for name, value in clsattrs.items():
            if isinstance(value, SchemaNode):
                value.name = name
                if value.raw_title is _marker:
                    value.title = name.replace('_', ' ').title()
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

def _Schema__new__(cls, *args, **kw):
    node = object.__new__(cls.node_type)
    node.name = None
    node._order = next(SchemaNode._counter)
    typ = cls.schema_type()
    node.__init__(typ, *args, **kw)
    for n in cls.nodes:
        node.add(n)
    return node

Schema = _SchemaMeta('Schema', (object,), 
    dict(schema_type=Mapping,
        node_type=SchemaNode,
        __new__=_Schema__new__))

MappingSchema = Schema


def _SequanceSchema__new__(cls, *args, **kw):
    node = object.__new__(cls.node_type)
    node.name = None
    node._order = next(SchemaNode._counter)
    typ = cls.schema_type()
    node.__init__(typ, *args, **kw)
    if not len(cls.nodes) == 1:
        raise Invalid(node,
                      'Sequence schemas must have exactly one child node')
    for n in cls.nodes:
        node.add(n)
    return node

SequenceSchema = _SchemaMeta('SequenceSchema', (object,),
    dict(schema_type=Sequence,
        node_type=SchemaNode,
        __new__=_SequanceSchema__new__))

class TupleSchema(Schema):
    schema_type = Tuple

class deferred(object):
    """ A decorator which can be used to define deferred schema values
    (missing values, widgets, validators, etc.)"""
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __call__(self, node, kw):
        return self.wrapped(node, kw)

def _unflatten_mapping(node, paths, fstruct,
                       get_child=None, rewrite_subpath=None):
    if get_child is None:
        get_child = node.__getitem__
    if rewrite_subpath is None:
        def rewrite_subpath(subpath):
            return subpath
    node_name = node.name
    prefix = node_name + '.'
    prefix_len = len(prefix)
    appstruct = {}
    subfstruct = {}
    subpaths = []
    curname = None
    for path in paths:
        if path == node_name:
            # flattened structs contain non-leaf nodes which are ignored
            # during unflattening.
            continue
        assert path.startswith(prefix), "Bad node: %s" % path
        subpath = path[prefix_len:]
        if '.' in subpath:
            name = subpath[:subpath.index('.')]
        else:
            name = subpath
        if curname is None:
            curname = name
        elif name != curname:
            subnode = get_child(curname)
            appstruct[curname] = subnode.typ.unflatten(
                subnode, subpaths, subfstruct)
            subfstruct = {}
            subpaths = []
            curname = name
        subpath = rewrite_subpath(subpath)
        subfstruct[subpath] = fstruct[path]
        subpaths.append(subpath)
    if curname is not None:
        subnode = get_child(curname)
        appstruct[curname] = subnode.typ.unflatten(
            subnode, subpaths, subfstruct)
    return appstruct
