.. _serializing_default_and_null:

Serializing Default and Null Values
===================================

Two sentinel values have special meanings during serialization:
:attr:`colander.default` and :attr:`colander.null`.  Both
:attr:`colander.default` and :attr:`colander.null` are used as
sentinel values during the serialization process, but each
represents a very different concept.

:attr:`colander.default` is a sentinel value which may be present in a
data structure passed to the :meth:`colander.SchemaNode.serialize`
method.  The presence of :attr:`colander.default` indicates that the
value it represents is missing in the data structure passed to
:meth:`colander.SchemaNode.serialize`, and, if possible, the *default
value* for the corresponding node should be serialized instead (see
:ref:`serializing_default`).

.. note::

   It makes sense for :attr:`colander.default` to be present in the
   data structure passed to the :meth:`colander.SchemaNode.serialize`
   method but it should not be present in a schema definition.  For
   example, it is unreasonable to use the :attr:`colander.default`
   value itself as the ``default`` argument to a
   :class:`colander.SchemaNode` constructor; passing it as ``default``
   will not do anything useful.  Use of :attr:`colander.default`
   during a schema definition is not prevented by the framework; it
   just doesn't make a lot of sense and may have unpredictable
   results.

:attr:`colander.null` is a sentinel representing that the *null* value
for a corresponding node should be serialized (see
:ref:`serializing_null`). The :attr:`colander.null` value may be
present directly in the data structure passed to the serialize method
but it is also not uncommon for :attr:`colander.null` to be the
*default value* for a node.

.. note::

   Unlike :attr:`colander.default`, :attr:`colander.null` is useful
   both within the data structure passed to
   :class:`colander.SchemaNode.serialize` and within a schema
   definition.

.. _serializing_default:

Serializing The :attr:`colander.default` Value and Other Missing Values
-----------------------------------------------------------------------

A node will attempt to serialize its ``default`` attribute during
:meth:`colander.SchemaNode.serialize` if a value it is provided is
*unspecified*.  *Unspecified* means:

#) The value expected by the schema is present in the data structure
   passed to :met:`colander.SchemaNode.serialize` but it is the
   literal value :attr:`colander.default`.

#) The value expected by the schema is a subkey of a mapping, but that
   key is missing from the mapping in the data structure passed to
   :meth:`colander.SchemaNode.serialize`:

The *default value* of a node is specified during schema creation.
For example, the ``hair_color`` node below has a default value of
``brown``:

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
   node is not a behavior shared by both serialization and
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
-------------------------------------------

The value :attr:`colander.null` has special meaning to types during
serialization.  If :attr:`colander.null` is used as a serialization
value to a type, it signals that the type should serialize a
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
:class:`colander.Integer` type is asked to serialize the
:attr:`colander.null` value, its ``serialize`` method simply returns
the :attr:`colander.null` value.  Therefore, when
:attr:`colander.null` is used as input to serialization, or as the
default value of a schema node, it is possible that the
:attr:`colander.null` value is placed into the serialized data
structure.  The consumer of the serialization must anticipate this and
deal with the special :attr:`colander.null` value in the output
however it sees fit.

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
'age':<unprintable colander null object>}``. We did not include the
``age`` attribute in the data we fed to ``serialize``, but there was a
``default`` value associated with ``age`` to fall back to:
:attr:`colander.null`.  However, the :class:`colander.Int` type cannot
serialize null to any *particular* integer, so it returns the
:attr:`colander.null` object itself.  As a result, the raw
:attr:`colander.null` value is simply injected into the resulting
serialization.  The caller of the
:meth:`colander.SchemaNode.serialize` method will need to deal with
this value appropriately.

Serialization Combinations
--------------------------

To reduce the potential for confusion about the difference between
:attr:`colander.default` and :attr:`colander.null`, here's a table of
serialization combinations.  Within this table, the ``Value`` column
represents the value passed to the
:meth:`colander.SchemaNode.serialize` method of a particular schema
node, the ``Default`` column represents the default value of that
schema node, and the ``Result`` column is a description of the result
of invoking the :meth:`colander.SchemaNode.serialize` method of the
schema node with the value.

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
   in which a key present in the schema is not present in a mapping
   passed to the :meth:`colander.SchemaNode.serialize` method.  In
   reality, ``<missing>`` means exactly the same thing as
   :attr:`colander.default`, because the :class:`colander.Mapping`
   code does the equivalent of ``mapping.get(keyname, colander.default)``
   to find a subvalue during serialization.

.. _deserializing_default_and_null:

Deserializing The Null Value
============================

The data structure passed to :meth:`colander.SchemaNode.deserialize`
may contain one or more :attr:`colander.null` sentinel markers.  The
meaning of :attr:`colander.null` as a sentinel marker during
deserialization is slightly different than the meaning of a
:attr:`colander.null` found during serialization.

When a :attr:`colander.null` sentinel marker is passed to the
:meth:`colander.SchemaNode.deserialize` method of a particular node in
a schema, the node will take the following steps:

- If the schema node has a valid ``missing`` attribute (the node's
  constructor was supplied with a ``missing`` value),


