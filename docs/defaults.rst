.. _default_and_null:

Default and Null Values
=======================

Two sentinel values have special meanings during serialization and
deserialization: :attr:`colander.default` and :attr:`colander.null`.
Both :attr:`colander.default` and :attr:`colander.null` are used as
sentinel values during the serialization and deserialization
processes, but they are not equivalent.  Each represents a different
concept.

:attr:`colander.default` is a sentinel value which may be passed to
:meth:`colander.SchemaNode.serialize` or to
:meth:`colander.SchemaNode.deserialize`.  The use of
:attr:`colander.default` indicates that the value corresponding to the
node it's passed to is missing, and if possible, the *default value*
(during serialization, see :ref:`serializing_default`) or *missing
value* (during deserialization, see :ref:`deserializing_default`) for
the corresponding node should be used instead.

.. note::

   It makes sense for :attr:`colander.default` to be present in a data
   structure passed to :meth:`colander.SchemaNode.serialize` or to
   :meth:`colander.SchemaNode.deserialize` but it should never be
   present in a schema definition and it should never be present in
   the output of a serialization or deserialization.  For example, it
   is not reasonable to use the :attr:`colander.default` value itself
   as the ``default`` or ``missing`` argument to a
   :class:`colander.SchemaNode` constructor.  Passing
   :attr:`colander.default` as the ``default`` or ``missing``
   arguments to a schema node constructor will not do anything useful
   (it is not explicitly prevented, it's just nonsensical).
   :attr:`colander.default` should also never be present in the result
   of serialization or the result of deserialization: it will only
   ever be present in the input, never in the output.

:attr:`colander.null` is a sentinel representing that the *null* value
for a corresponding node should be serialized (see
:ref:`serializing_null`) or deserialized (see
:ref:`deserializing_null`). The :attr:`colander.null` value may be
present directly in the data structure passed to
:meth:`colander.SchemaNode.serialize` or
:meth:`colander.SchemaNdoe.deserialize` but it is also not uncommon
for :attr:`colander.null` to be the *default value* (``default``) or
*missing value* (``missing``) for a node.

.. note::

   Unlike :attr:`colander.default`, :attr:`colander.null` is useful
   both within the data structure passed to
   :meth:`colander.SchemaNode.serialize` and
   :meth:`colander.SchemaNode.deserialize` and within a schema
   definition.

.. _serializing_default_and_null:

Serializing Default and Null Values
-----------------------------------

It is possible to serialize both the default and null values.

.. _serializing_default:

Serializing The :attr:`colander.default` Value
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A node will attempt to serialize its *default value* during
:meth:`colander.SchemaNode.serialize` if a value it is provided is
*unspecified*.  *Unspecified* means:

#) The value expected by the schema is present in the data structure
   passed to :meth:`colander.SchemaNode.serialize` but it is the
   literal value :attr:`colander.default`.

#) The value expected by the schema is a subkey of a mapping, but that
   key is missing from the mapping in the data structure passed to
   :meth:`colander.SchemaNode.serialize`:

The *default value* of a node is specified during schema creation as
its ``default`` attribute / argument.  For example, the ``hair_color``
node below has a default value of ``brown``:

.. code-block:: python

   import colander

   class Person(colander.MappingSchema):
       name = colander.SchemaNode(colander.String())
       age = colander.SchemaNode(colander.Int(),
                                 validator=colander.Range(0, 200))
       hair_color = colander.SchemaNode(colander.String(), default='brown')

Because the ``hair_color`` node is passed a ``default`` value, if the
above schema is used to serialize a mapping that does not have a
``hair_color`` key, the default will be serialized:

.. code-block:: python

   schema = Person()
   serialized = schema.serialize({'name':'Fred', 'age':20})

Even though we did not include the ``hair_color`` attribute in the
data we fed to ``serialize``, the value of ``serialized`` above will
be ``{'name':'Fred, 'age':'20', 'hair_color':'brown'}``.  This is due
to the ``default`` value provided during schema node construction for
``hair_color``.

The same outcome would have been true had we fed the schema a mapping
for serialization which had the :attr:`colander.default` sentinel as
the ``hair_color`` value:

.. code-block:: python

   from colander import default
   schema = Person()
   serialized = schema.serialize({'name':'Fred', 'age':20, 
                                  'hair_color':default})

In the above, the value of ``serialized`` above will be
``{'name':'Fred, 'age':'20', 'hair_color':'brown'}`` just as it was in
the example where ``hair_color`` was not present in the mapping.

On the other hand, if the ``hair_color`` value is missing or
:attr:`colander.default`, and the schema does *not* name a ``default``
value for ``hair_color``, it will be present in the resulting
serialization as :attr:`colander.null`:

.. code-block:: python

   import colander

   class Person(colander.MappingSchema):
       name = colander.SchemaNode(colander.String())
       age = colander.SchemaNode(colander.Int(),
                                 validator=colander.Range(0, 200))
       hair_color = colander.SchemaNode(colander.String())


   schema = Person()
   serialized = schema.serialize({'name':'Fred', 'age':20})

The value for ``serialized`` above will be ``{'name':'Fred,
'age':'20', 'hair_color':colander.null}``. We did not include the
``hair_color`` attribute in the data we fed to ``serialize``, and
there was no ``default`` value associated with ``hair_color`` to fall
back to, so the :attr:`colander.null` value is used in the resulting
serialization.

Serializations can be done of partial data structures; the
:attr:`colander.null` value is inserted into the serialization
whenever a corresponding value in the data structure being serialized
is missing.

.. note:: The injection of the :attr:`colander.null` value into a
   serialization when a default doesn't exist for the corresponding
   node is not a behavior shared during both serialization and
   deserialization.  While a *serialization* can be performed against
   a partial data structure without corresponding node defaults, a
   *deserialization* cannot be done to partial data without
   corresponding node ``missing`` values.  When a value is missing
   from a data structure being deserialized, and no ``missing`` value
   exists for the node corresponding to the missing item in the data
   structure, a :class:`colander.Invalid` exception will be the
   result.

.. _serializing_null:

Serializing The :attr:`colander.null` Value
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The value :attr:`colander.null` has special meaning to types during
serialization.  If :attr:`colander.null` is used as the serialization
value passed to a type, it signals that the type should serialize a
type-specific *null value*.

Serialization of a *null value* is completely type-specific, meaning
each type is free to serialize :attr:`colander.null` to a value that
makes sense for that particular type.  For example, the null
serialization value of a :class:`colander.String` type is the empty
string.

The :attr:`colander.null` value will be passed to a type either
directly or indirectly:

- directly: because :attr:`colander.null` is passed directly to the
  ``serialize`` method of a node.

- indirectly: because a node uses a :attr:`colander.null` value as its
  ``default`` attribute and the value passed to the serialize method
  of a node is missing or :attr:`colander.default` (see
  :ref:`serializing_default_and_null`).

When a particular type cannot serialize the null value to anything
sensible, the type's serialize method must return the null object
itself as a serialization.  For example, when the
:class:`colander.Boolean` type is asked to serialize the
:attr:`colander.null` value, its ``serialize`` method simply returns
the :attr:`colander.null` value (because null is conceptually neither
true nor false).  Therefore, when :attr:`colander.null` is used as
input to serialization, or as the default value of a schema node, it
is possible that the :attr:`colander.null` value will placed into the
serialized data structure.  The consumer of the serialization must
anticipate this and deal with the special :attr:`colander.null` value
in the output however it sees fit.

Here's an example of a serialization which will have the sentinel
value :attr:`colander.null` in the serialized output:

.. code-block:: python

   import colander

   class Person(colander.MappingSchema):
       name = colander.SchemaNode(colander.String())
       age = colander.SchemaNode(colander.Int(), default=colander.null)

Because the ``age`` node is passed a ``default`` value of
:attr:`colander.null`, if the above schema is used to serialize a
mapping that does not have an ``age`` key, the default will be
serialized into the output:

.. code-block:: python

   schema = Person()
   serialized = schema.serialize({'name':'Fred'})

The value for ``serialized`` above will be ``{'name':'Fred,
'age':colander.null}``. We did not include the ``age`` attribute in
the data we fed to ``serialize``, but there was a ``default`` value
associated with ``age`` to fall back to: :attr:`colander.null`.
However, the :class:`colander.Int` type cannot serialize null to any
*particular* integer, so it returns the :attr:`colander.null` object
itself.  As a result, the raw :attr:`colander.null` value is simply
injected into the resulting serialization.  The caller of the
:meth:`colander.SchemaNode.serialize` method will need to deal with
this value appropriately.

Serialization Combinations
~~~~~~~~~~~~~~~~~~~~~~~~~~

To reduce the potential for confusion about the difference between
:attr:`colander.default` and :attr:`colander.null` during
serialization, here's a table of serialization combinations.  Within
this table, the ``Value`` column represents the value passed to the
:meth:`colander.SchemaNode.serialize` method of a particular schema
node, the ``Default`` column represents the ``default`` value of that
schema node, and the ``Result`` column is a description of the result
of invoking the :meth:`colander.SchemaNode.serialize` method of the
schema node with the effective value.

===================== ===================== ===========================
Value                 Default               Result
===================== ===================== ===========================
colander.default      <missing>             Invalid exception raised
<missing>             <missing>             Invalid exception raised
colander.default      value                 value serialized
<missing>             value                 value serialized
colander.default      colander.null         null serialized
<missing>             colander.null         null serialized
value                 <missing>             value serialized
value_a               value_b               value_a serialized
value                 colander.null         value serialized
colander.null         <missing>             null serialized
colander.null         value                 null serialized
colander.null         colander.null         null serialized
===================== ===================== ===========================

.. note:: ``<missing>`` in the above table represents the circumstance
   in which a key present in a :class:`colander.MappingSchema` is not
   present in a mapping passed to its
   :meth:`colander.SchemaNode.serialize` method.  In reality,
   ``<missing>`` means exactly the same thing as
   :attr:`colander.default`, because the :class:`colander.Mapping`
   type does the equivalent of ``mapping.get(keyname,
   colander.default)`` to find a subvalue during serialization.

.. _deserializing_default_and_null:

Deserializing Default and Null Values
-------------------------------------

It is possible to deserialize both the default and null values.

.. _deserializing_default:

Deserializing The :attr:`colander.default` Value
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The data structure passed to :meth:`colander.SchemaNode.deserialize`
may contain one or more :attr:`colander.default` sentinel markers.

When a :attr:`colander.default` sentinel marker is passed to the
:meth:`colander.SchemaNode.deserialize` method of a particular node in
a schema, the node will take the following steps:

- If the schema node has a valid ``missing`` attribute (the node's
  constructor was supplied with a ``missing`` argument), the
  ``missing`` value will be returned.  Note that when this happens,
  the ``missing`` value is not validated by any schema node validator:
  it is simply returned.

- If the schema node does *not* have a valid ``missing`` attribute
  (the node's constructor was not supplied with a ``missing`` value),
  a :exc:`colander.Invalid` exception will be raised with a message
  indicating that the field is required.

.. note:: There are differences between serialization and
   deserialization involving the :attr:`colander.default` value.
   During serialization, if an :attr:`colander.default` value is
   encountered, and no valid ``default`` attribute exists on the node
   related to the value, a :attr:`colander.null` attribute is
   returned.  The the first difference: deserialization doesn't use
   the ``default`` attribute of the node to find a default value in
   the same circumstance; instead it uses the ``missing`` attribute.
   The second difference: if, during deserialization, an
   :attr:`colander.default` value is encountered as the value passed
   to the deserialize method, and no valid ``missing`` value exists
   for the node, a :exc:`colander.Invalid` exception is raised
   (:attr:`colander.null` is not returned, as it is during
   serialization).

.. _deserializing_null:

Deserializing The :attr:`colander.null` Value
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The value :attr:`colander.null` has special meaning to types during
deserialization.  If :attr:`colander.null` is used as a
deserialization value to a type, it signals that the type should
deserialize the type-specific *null value*.

Deserialization of a *null value* is completely type-specific, meaning
each type is free to deserialize :attr:`colander.null` to a value that
makes sense for that particular type.  For example, the
deserialization of a :class:`colander.String` type is the empty
string.

The :attr:`colander.null` value will be passed to a type either
directly or indirectly:

- directly: because :attr:`colander.null` is passed directly to the
  ``deserialize`` method of a node.

- indirectly: because a node uses a :attr:`colander.null` value as its
  ``missing`` attribute and the value passed to the serialize method
  of a node is missing or :attr:`colander.default`.

When a particular type cannot deserialize the null value to anything
sensible, the type's deserialize method must return the null object
itself as a serialization.

For example, when the :class:`colander.Boolean` type is asked to
deserialize the :attr:`colander.null` value, its ``deserialize``
method simply returns the :attr:`colander.null` value (because null is
conceptually neither true nor false).  Therefore, when
:attr:`colander.null` is used as input to deserialization, or as the
``missing`` value of a schema node, it is possible that the
:attr:`colander.null` value will be placed into the deserialized data
structure.  The consumer of the deserialization must anticipate this
and deal with the special :attr:`colander.null` value in the output
however it sees fit.

Note that deserialization of the null value never invokes a validator.

Deserialization Combinations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To reduce the potential for confusion about the difference between
:attr:`colander.default` and :attr:`colander.null` during
deserialization, here's a table of serialization combinations.  Within
this table, the ``Value`` column represents the value passed to the
:meth:`colander.SchemaNode.deserialize` method of a particular schema
node, the ``Missing`` column represents the ``missing`` value of that
schema node, and the ``Result`` column is a description of the result
of invoking the :meth:`colander.SchemaNode.deserialize` method of the
schema node with the effective value.

===================== ===================== ===========================
Value                 Missing               Result
===================== ===================== ===========================
colander.default      <missing>             Invalid exception raised
<missing>             <missing>             Invalid exception raised
colander.default      value                 value deserialized
<missing>             value                 value deserialized
colander.default      colander.null         null deserialized
<missing>             colander.null         null deserialized
value                 <missing>             value deserialized
value_a               value_b               value_a deserialized
value                 colander.null         value deserialized
colander.null         <missing>             null deserialized
colander.null         value                 null deserialized
colander.null         colander.null         null deserialized
===================== ===================== ===========================

.. note:: ``<missing>`` in the above table represents the circumstance
   in which a key present in a :class:`colander.MappingSchema` is not
   present in a mapping passed to its
   :meth:`colander.SchemaNode.deserialize` method.  In reality,
   ``<missing>`` means exactly the same thing as
   :attr:`colander.default`, because the :class:`colander.Mapping`
   type does the equivalent of ``mapping.get(keyname,
   colander.default)`` to find a subvalue during deserialization.

