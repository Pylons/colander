Colander API
------------

Exceptions
~~~~~~~~~~

.. automodule:: colander

  .. autoclass:: Invalid
     :members:

     .. attribute:: pos

        An integer representing the position of this exception's
        schema node relative to all other child nodes of this
        exception's parent schema node.  For example, if this
        exception is related to the third child node of its parent's
        schema, ``pos`` might be the integer ``3``.  ``pos`` may also
        be ``None``, in which case this exception is the root
        exception.

     .. attribute:: children

        A list of child exceptions.  Each element in this list (if
        any) will also be an :exc:`colander.Invalid` exception,
        recursively, representing the error circumstances for a
        particular schema deserialization.

     .. attribute:: msg

       A ``str`` or ``unicode`` object, or a *translation string*
       instance representing a freeform error value set by a
       particular type during an unsuccessful deserialization.  If
       this exception is only structural (only exists to be a parent
       to some inner child exception), this value will be ``None``.

     .. attribute:: node

       The schema node to which this exception relates.

     .. attribute:: value

       An attribute not used internally by Colander, but which can be
       used by higher-level systems to attach arbitrary values to
       Colander exception nodes.  For example, In the system named
       Deform, which uses Colander schemas to define HTML form
       renderings, the ``value`` is used when raising an exception
       from a widget as the value which should be redisplayed when an
       error is shown.

Validators
~~~~~~~~~~

  .. autoclass:: All

  .. autoclass:: Range

  .. autoclass:: Length

  .. autoclass:: OneOf

  .. autoclass:: Function

  .. autoclass:: Regex

  .. autoclass:: Email

Types
~~~~~

  .. autoclass:: Mapping

  .. autoclass:: Tuple

  .. autoclass:: Sequence

  .. autoclass:: Seq

  .. autoclass:: String

  .. autoclass:: Str

  .. autoclass:: Integer

  .. autoclass:: Int

  .. autoclass:: Float

  .. autoclass:: Decimal

  .. autoclass:: Boolean

  .. autoclass:: Bool

  .. autoclass:: GlobalObject

  .. autoclass:: DateTime

  .. autoclass:: Date

  .. autoclass:: Time

Schema-Related
~~~~~~~~~~~~~~

  .. autoclass:: SchemaNode
     :members:

     .. automethod:: __delitem__

     .. automethod:: __getitem__

     .. automethod:: __iter__

  .. autoclass:: Schema

  .. autoclass:: MappingSchema

  .. autoclass:: TupleSchema

  .. autoclass:: SequenceSchema

  .. autoclass:: deferred

  .. attribute:: null

     Represents a null value in colander-related operations.

  .. attribute:: required

     Represents a required value in colander-related operations.
