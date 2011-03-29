.. _null:

The Null Value
==============

:attr:`colander.null` is a sentinel value which may be passed to
:meth:`colander.SchemaNode.serialize` during serialization or to
:meth:`colander.SchemaNode.deserialize` during deserialization.

During serialization, the use of :attr:`colander.null` indicates that
the :term:`appstruct` value corresponding to the node it's passed to
is missing and the value of the ``default`` attribute of the
corresponding node should be used instead.

During deserialization, the use of :attr:`colander.null` indicates
that the :term:`cstruct` value corresponding to the node it's passed
to is missing, and if possible, the value of the ``missing`` attribute
of the corresponding node should be used instead.

Note that :attr:`colander.null` has no relationship to the built-in Python
``None`` value.  ``colander.null`` is used instead of ``None`` because
``None`` is a potentially valid value for some serializations and
deserializations, and using it as a sentinel would prevent ``None`` from
being used in this way.

.. _serializing_null:

Serializing The Null Value
--------------------------

A node will attempt to serialize its *default value* during
:meth:`colander.SchemaNode.serialize` if the value it is passed as an
``appstruct`` argument is the :attr:`colander.null` sentinel value.

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
appstruct we fed to ``serialize``, the value of ``serialized`` above
will be ``{'name':'Fred, 'age':'20', 'hair_color':'brown'}``.  This is
because a ``default`` value of ``brown`` was provided during schema
node construction for ``hair_color``.

The same outcome would have been true had we fed the schema a mapping
for serialization which had the :attr:`colander.null` sentinel as the
``hair_color`` value:

.. code-block:: python

   import colander

   schema = Person()
   serialized = schema.serialize({'name':'Fred', 'age':20, 
                                  'hair_color':colander.null})

When the above is run, the value of ``serialized`` will be
``{'name':'Fred, 'age':'20', 'hair_color':'brown'}`` just as it was in
the example where ``hair_color`` was not present in the mapping.

As we can see, serializations may be done of partial data structures;
the :attr:`colander.null` value is inserted into the serialization
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

If, during serialization, a value for the node is missing from the
cstruct and the node does not possess an explicit *default value*, the
:attr:`colander.null` sentinel value is passed to the type's
``serialize`` method directly, instructing the type to serialize a
type-specific *null value*.

Serialization of a null value is completely type-specific, meaning
each type is free to serialize :attr:`colander.null` to a value that
makes sense for that particular type.  For example, the null
serialization value of a :class:`colander.String` type is the empty
string.

For example:

.. code-block:: python

   import colander

   class Person(colander.MappingSchema):
       name = colander.SchemaNode(colander.String())
       age = colander.SchemaNode(colander.Int(),
                                 validator=colander.Range(0, 200))
       hair_color = colander.SchemaNode(colander.String())


   schema = Person()
   serialized = schema.serialize({'name':'Fred', 'age':20})

In the above example, the ``hair_color`` value is missing and the
schema does *not* name a ``default`` value for ``hair_color``.
However, when we attempt to serialize the data structure, an error is
not raised.  Instead, the value for ``serialized`` above will be
``{'name':'Fred, 'age':'20', 'hair_color':colander.null}``.

Because we did not include the ``hair_color`` attribute in the data we
fed to ``serialize``, and there was no ``default`` value associated
with ``hair_color`` to fall back to, the :attr:`colander.null` value
is passed as the ``appstruct`` value to the ``serialize`` method of
the underlying type (:class:`colander.String`).  The return value of
that type's ``serialize`` method when :attr:`colander.null` is passed
as the ``appstruct`` is placed into the serialization.
:class:`colander.String` happens to *return* :attr:`colander.null`
when it is passed :attr:`colander.null` as its appstruct argument, so
this is what winds up in the resulting cstruct.

The :attr:`colander.null` value will be passed to a type either
directly or indirectly:

- directly: because :attr:`colander.null` is passed directly to the
  ``serialize`` method of a node.

- indirectly: because every schema node uses a :attr:`colander.null`
  value as its ``default`` attribute when no explicit default is
  provided.

When a particular type cannot serialize the null value to anything
sensible, that type's ``serialize`` method must return the null object
itself as a serialization.  For example, when the
:class:`colander.Boolean` type is asked to serialize the
:attr:`colander.null` value, its ``serialize`` method simply returns
the :attr:`colander.null` value (because null is conceptually neither
true nor false).

Therefore, when :attr:`colander.null` is used as input to
serialization, or as the default value of a schema node, it is
possible that the :attr:`colander.null` value will placed into the
serialized data structure.  The consumer of the serialization must
anticipate this and deal with the special :attr:`colander.null` value
in the output however it sees fit.

Serialization Combinations
~~~~~~~~~~~~~~~~~~~~~~~~~~

Within this table, the ``Value`` column represents the value passed to
the :meth:`colander.SchemaNode.serialize` method of a particular
schema node, the ``Default`` column represents the ``default`` value
of that schema node, and the ``Result`` column is a description of the
result of invoking the :meth:`colander.SchemaNode.serialize` method of
the schema node with the effective value.

===================== ===================== ===========================
Value                 Default               Result
===================== ===================== ===========================
colander.null         value                 value serialized
<missing>             value                 value serialized
colander.null         colander.null         null serialized
<missing>             colander.null         null serialized
value                 <missing>             value serialized
value_a               value_b               value_a serialized
value                 colander.null         value serialized
colander.null         <missing>             null serialized
colander.null         value                 null serialized
===================== ===================== ===========================

.. note:: ``<missing>`` in the above table represents the circumstance
   in which a key present in a :class:`colander.MappingSchema` is not
   present in a mapping passed to its
   :meth:`colander.SchemaNode.serialize` method.  In reality,
   ``<missing>`` means exactly the same thing as
   :attr:`colanderr.null`, because the :class:`colander.Mapping` type
   does the equivalent of ``mapping.get(keyname, colander.null)`` to
   find a subvalue during serialization.

.. _deserializing_null:

Deserializing The Null Value
----------------------------

The data structure passed to :meth:`colander.SchemaNode.deserialize`
may contain one or more :attr:`colander.null` sentinel markers.

When a :attr:`colander.null` sentinel marker is passed to the
:meth:`colander.SchemaNode.deserialize` method of a particular node in
a schema, the node will take the following steps:

- The *type* object's ``deserialize`` method will be called with the null
  value to allow the type to convert the null value to a type-specific
  default.  The resulting "appstruct" is used instead of the value passed
  directly to :meth:`colander.SchemaNode.deserialize` in subsequent
  operations.  Most types, when they receive the ``null`` value will simply
  return it, however.

- If the appstruct value computed by the type's ``deserialize`` method is
  ``colander.null`` and the schema node has an explicit ``missing`` attribute
  (the node's constructor was supplied with an explicit ``missing``
  argument), the ``missing`` value will be returned.  Note that when this
  happens, the ``missing`` value is not validated by any schema node
  validator: it is simply returned.

- If the appstruct value computed by the type's ``deserialize`` method is
  ``colander.null`` and the schema node does *not* have an explicitly
  provided ``missing`` attribute (the node's constructor was not supplied
  with an explicit ``missing`` value), a :exc:`colander.Invalid` exception
  will be raised with a message indicating that the field is required.

.. note:: There are differences between serialization and
   deserialization involving the :attr:`colander.null` value.  During
   serialization, if an :attr:`colander.null` value is encountered,
   and no valid ``default`` attribute exists on the node related to
   the value the *null value* for that node is returned.
   Deserialization, however, doesn't use the ``default`` attribute of
   the node to find a default deserialization value in the same
   circumstance; instead it uses the ``missing`` attribute instead.
   Also, if, during deserialization, an :attr:`colander.null` value is
   encountered as the value passed to the deserialize method, and no
   explicit ``missing`` value exists for the node, a
   :exc:`colander.Invalid` exception is raised (:attr:`colander.null`
   is not returned, as it is during serialization).

Here's an example of a deserialization which uses a ``missing`` value
in the schema as a deserialization default value:

.. code-block:: python

   import colander

   class Person(colander.MappingSchema):
       name = colander.SchemaNode(colander.String())
       age = colander.SchemaNode(colander.Int(), missing=None)

   schema = Person()
   deserialized = schema.deserialize({'name':'Fred', 'age':colander.null})

The value for ``deserialized`` above will be ``{'name':'Fred,
'age':None}``.

Because the ``age`` schema node is provided a ``missing`` value of
``None``, if that schema is used to deserialize a mapping that has an
an ``age`` key of :attr:`colander.null`, the ``missing`` value of
``None`` is serialized into the appstruct output for ``age``.

.. note:: Note that ``None`` can be used for the ``missing`` schema
   node value as required, as in the above example.  It's no different
   than any other value used as ``missing``.  The empty string can
   also be used as the ``missing`` value if that is helpful.

The :attr:`colander.null` value is also the default, so it needn't be
specified in the cstruct.  Therefore, the ``deserialized`` value of
the below is equivalent to the above's:

.. code-block:: python

   import colander

   class Person(colander.MappingSchema):
       name = colander.SchemaNode(colander.String())
       age = colander.SchemaNode(colander.Int(), missing=None)

   schema = Person()
   deserialized = schema.deserialize({'name':'Fred'})

Deserialization Combinations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Within this table, the ``Value`` column represents the value passed to
the :meth:`colander.SchemaNode.deserialize` method of a particular
schema node, the ``Missing`` column represents the ``missing`` value
of that schema node, and the ``Result`` column is a description of the
result of invoking the :meth:`colander.SchemaNode.deserialize` method
of the schema node with the effective value.

===================== ===================== ===========================
Value                 Missing               Result
===================== ===================== ===========================
colander.null         <missing>             Invalid exception raised
<missing>             <missing>             Invalid exception raised
colander.null         value                 value used
<missing>             value                 value used
<missing>             colander.null         colander.null used
value                 <missing>             value used
value                 colander.null         value used
value_a               value_b               value_a used
===================== ===================== ===========================

.. note:: ``<missing>`` in the above table represents the circumstance
   in which a key present in a :class:`colander.MappingSchema` is not
   present in a mapping passed to its
   :meth:`colander.SchemaNode.deserialize` method.  In reality,
   ``<missing>`` means exactly the same thing as
   :attr:`colander.null`, because the :class:`colander.Mapping`
   type does the equivalent of ``mapping.get(keyname,
   colander.null)`` to find a subvalue during deserialization.

