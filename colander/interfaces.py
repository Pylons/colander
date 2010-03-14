def Validator(struct, value):
    """
    A validator is called after deserialization of a value.
    
    If ``value`` is not valid, raise a :class:`colander.Invalid`
    instance as an exception after.

    ``struct`` is a :class:`colander.Structure` instance which
    contains, among other things, the default value, the name of the
    value, and a ``required`` flag indicating whether this value is
    required.  It is often ignored in simple validators.
    """

class Type(object):
    def serialize(self, struct, value):
        """
        Serialize the object represented by ``value`` to a
        data structure.  The serialization should be composed of one or
        more objects which can be deserialized by the
        :meth:`colander.interfaces.Type.deserialize` method of this
        type.

        This method should also do type validation of ``value``.

        ``struct`` is a :class:`colander.Structure` instance which
        contains, among other things, the default value, the name of
        the value, and a ``required`` flag indicating whether this
        value is required.

        If the object cannot be serialized, or type validation for
        ``value`` fails, a :exc:`colander.Invalid` exception should be
        raised.
        """

    def deserialize(self, struct, value):
        """

        Deserialze the serialization represented by ``value`` to a
        data structure.  The deserialization should be composed of one
        or more objects which can be serialized by the
        :meth:`colander.interfaces.Type.serialize` method of this
        type.

        This method should also do type validation of ``value``.

        ``struct`` is a :class:`colander.Structure` instance which
        contains, among other things, the default value, the name of
        the value, and a ``required`` flag indicating whether this
        value is required.

        If the object cannot be deserialized, or type validation for
        ``value`` fails, a :exc:`colander.Invalid` exception should be
        raised.
        """
        
