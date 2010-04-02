Colander
========

Colander is useful as a system for validating and deserializing data
obtained via XML, JSON, an HTML form post or any other equally simple
data serialization.  Colander can be used to:

- Define a data schema

- Deserialize a data structure composed of strings, mappings, and
  lists into an arbitrary Python structure after validating the data
  structure against a data schema.

- Serialize an arbitrary Python structure to a data structure composed
  of strings, mappings, and lists.

Out of the box, Colander can serialize and deserialize various types
of objects, including:

- A mapping object (e.g. dictionary)

- A variable-length sequence of objects (each object is of the same
  type).

- A fixed-length tuple of objects (each object is of a different
  type).

- A string or Unicode object.

- An integer.

- A float.

- A boolean.

- An importable Python object (to a dotted Python object path).

- A Python ``datetime.datetime`` object.

- A Python ``datetime.date`` object.

Colander allows additional data structures to be serialized and
deserialized by allowing a developer to define new "types".

Defining A Colander Schema
--------------------------

Imagine you want to deserialize and validate a serialization of data
you've obtained by reading a YAML document.  An example of such a data
serialization might look something like this:

.. code-block:: python
   :linenos:

   {
    'name':'keith',
    'age':'20',
    'friends':[('1', 'jim'),('2', 'bob'), ('3', 'joe'), ('4', 'fred')],
    'phones':[{'location':'home', 'number':'555-1212'},
              {'location':'work', 'number':'555-8989'},],
   }

Let's further imagine you'd like to make sure, on demand, that a
particular serialization of this type read from this YAML document or
another YAML document is "valid".

Notice that all the innermost values in the serialization are strings,
even though some of them (such as age and the position of each friend)
are more naturally integer-like.  Let's define a schema which will
attempt to convert a serialization to a data structure that has
different types.

.. code-block:: python
   :linenos:

   import colander

   class Friend(colander.TupleSchema):
       rank = colander.SchemaNode(colander.Int(), 
                                 validator=colander.Range(0, 9999))
       name = colander.SchemaNode(colander.String())

   class Phone(colander.MappingSchema):
       location = colander.SchemaNode(colander.String(), 
                                     validator=colander.OneOf(['home', 'work']))
       number = colander.SchemaNode(colander.String())

   class Friends(colander.SequenceSchema):
       friend = Friend()

   class Phones(colander.SequenceSchema):
       phone = Phone()

   class Person(colander.MappingSchema):
       name = colander.SchemaNode(colander.String())
       age = colander.SchemaNode(colander.Int(),
                                validator=colander.Range(0, 200))
       friends = Friends()
       phones = Phones()
       
For ease of reading, we've actually defined *five* schemas above, but
we coalesce them all into a single ``Person`` schema.  As the result
of our definitions, a ``Person`` represents:

- A ``name``, which must be a string.

- An ``age``, which must be deserializable to an integer; after
  deserialization happens, a validator ensures that the integer is
  between 0 and 200 inclusive.

- A sequence of ``friend`` structures.  Each friend structure is a
  two-element tuple.  The first element represents an integer rank; it
  must be between 0 and 9999 inclusive.  The second element represents
  a string name.

- A sequence of ``phone`` structures.  Each phone structure is a
  mapping.  Each phone mapping has two keys: ``location`` and
  ``number``.  The ``location`` must be one of ``work`` or ``home``.
  The number must be a string.

Schema Node Objects
~~~~~~~~~~~~~~~~~~~

A schema is composed of one or more *schema node* objects, each
typically of the class :class:`colander.SchemaNode`, usually in a
nested arrangement.  Each schema node object has a required *type*, an
optional deserialization *validator*, an optional *default*, an
optional *title*, an optional *description*, and a slightly less
optional *name*.

The *type* of a schema node indicates its data type (such as
:class:`colander.Int` or :class:`colander.String`).

The *validator* of a schema node is called after deserialization; it
makes sure the deserialized value matches a constraint.  An example of
such a validator is provided in the schema above:
``validator=colander.Range(0, 200)``.  A validator is not called after
serialization, only after deserialization.

The *default* of a schema node indicates its default value if a value
for the schema node is not found in the input data during
serialization and deserialization.  It should be the *deserialized*
representation.  If a schema node does not have a default, it is
considered required.

The *name* of a schema node appears in error reports.

The *title* of a schema node is metadata about a schema node that can
be used by higher-level systems.  By default, it is a capitalization
of the *name*.

The *description* of a schema node is metadata about a schema node
that can be used by higher-level systems.  By default, it is empty.

The name of a schema node that is introduced as a class-level
attribute of a :class:`colander.MappingSchema`,
:class:`colander.TupleSchema` or a :class:`colander.SequenceSchema` is
its class attribute name.  For example:

.. code-block:: python
   :linenos:

   import colander

   class Phone(colander.MappingSchema):
       location = colander.SchemaNode(colander.String(), 
                                     validator=colander.OneOf(['home', 'work']))
       number = colander.SchemaNode(colander.String())

The name of the schema node defined via ``location =
colander.SchemaNode(..)`` within the schema above is ``location``.
The title of the same schema node is ``Location``.

Schema Objects
~~~~~~~~~~~~~~

In the examples above, if you've been paying attention, you'll have
noticed that we're defining classes which subclass from
:class:`colander.MappingSchema`, :class:`colander.TupleSchema` and
:class:`colander.SequenceSchema`.  

It's turtles all the way down: the result of creating an instance of
any of :class:`colander.MappingSchema`, :class:`colander.TupleSchema`
or :class:`colander.SequenceSchema` object is *also* a
:class:`colander.SchemaNode` object.

Instantiating a :class:`colander.MappingSchema` creates a schema node
which has a *type* value of :class:`colander.Mapping`.

Instantiating a :class:`colander.TupleSchema` creates a schema node
which has a *type* value of :class:`colander.Tuple`.

Instantiating a :class:`colander.SequenceSchema` creates a schema node
which has a *type* value of :class:`colander.Sequence`.

Deserializing A Data Structure Using a Schema
---------------------------------------------

Earlier we defined a schema:

.. code-block:: python
   :linenos:

   import colander

   class Friend(colander.TupleSchema):
       rank = colander.SchemaNode(colander.Int(), 
                                 validator=colander.Range(0, 9999))
       name = colander.SchemaNode(colander.String())

   class Phone(colander.MappingSchema):
       location = colander.SchemaNode(colander.String(), 
                                     validator=colander.OneOf(['home', 'work']))
       number = colander.SchemaNode(colander.String())

   class Friends(colander.SequenceSchema):
       friend = Friend()

   class Phones(colander.SequenceSchema):
       phone = Phone()

   class Person(colander.MappingSchema):
       name = colander.SchemaNode(colander.String())
       age = colander.SchemaNode(colander.Int(),
                                validator=colander.Range(0, 200))
       friends = Friends()
       phones = Phones()

Let's now use this schema to try to deserialize some concrete data
structures.

Deserializing A Valid Serialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python
   :linenos:

     data = {
            'name':'keith',
            'age':'20',
            'friends':[('1', 'jim'),('2', 'bob'), ('3', 'joe'), ('4', 'fred')],
            'phones':[{'location':'home', 'number':'555-1212'},
                      {'location':'work', 'number':'555-8989'},],
            }
     schema = Person()
     deserialized = schema.deserialize(data)

When ``schema.deserialize(data)`` is called, because all the data in
the schema is valid, and the structure represented by ``data``
conforms to the schema, ``deserialized`` will be the following:

.. code-block:: python
   :linenos:

     {
     'name':'keith',
     'age':20,
     'friends':[(1, 'jim'),(2, 'bob'), (3, 'joe'), (4, 'fred')],
     'phones':[{'location':'home', 'number':'555-1212'},
               {'location':'work', 'number':'555-8989'},],
     }

Note that all the friend rankings have been converted to integers,
likewise for the age.

Deserializing An Invalid Serialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Below, the ``data`` structure has some problems.  The ``age`` is a
negative number.  The rank for ``bob`` is ``t`` which is not a valid
integer.  The ``location`` of the first phone is ``bar``, which is not
a valid location (it is not one of "work" or "home").  What happens
when a data structure cannot be deserialized due to a data type error
or a validation error?

.. code-block:: python
   :linenos:

     import colander

     data = {
            'name':'keith',
            'age':'-1',
            'friends':[('1', 'jim'),('t', 'bob'), ('3', 'joe'), ('4', 'fred')],
            'phones':[{'location':'bar', 'number':'555-1212'},
                      {'location':'work', 'number':'555-8989'},],
            }
     schema = Person()
     schema.deserialize(data)

The ``deserialize`` method will raise an exception, and the ``except``
clause above will be invoked, causing an error messaage to be printed.
It will print something like:

.. code-block:: python
   :linenos:

   Invalid: {'age':'-1 is less than minimum value 0',
            'friends.1.0':'"t" is not a number',
            'phones.0.location:'"bar" is not one of "home", "work"'}

The above error is telling us that:

- The top-level age variable failed validation.

- Bob's rank (the Friend tuple name ``bob``'s zeroth element) is not a
  valid number.

- The zeroth phone number has a bad location: it should be one of
  "home" or "work".

We can optionally catch the exception raised and obtain the raw error
dictionary:

.. code-block:: python
   :linenos:

     import colander

     data = {
            'name':'keith',
            'age':'-1',
            'friends':[('1', 'jim'),('t', 'bob'), ('3', 'joe'), ('4', 'fred')],
            'phones':[{'location':'bar', 'number':'555-1212'},
                      {'location':'work', 'number':'555-8989'},],
            }
     schema = Person()
     try:
         schema.deserialize(data)
     except colander.Invalid, e:
         errors = e.asdict()
         print errors

This will print something like:

.. code-block:: python
   :linenos:

   {'age':'-1 is less than minimum value 0',
    'friends.1.0':'"t" is not a number',
    'phones.0.location:'"bar" is not one of "home", "work"'}

Serialization
-------------

Serializing a data structure is obviously the inverse operation from
deserializing a data structure.  The ``serialize`` method of a schema
performs serialization of application data.  If you pass the
``serialize`` method data that can be understood by the schema types
in the schema you're calling it against, you will be returned a data
structure of serialized values.

For example, given the following schema:

.. code-block:: python
   :linenos:

   import colander

   class Person(colander.MappingSchema):
       name = colander.SchemaNode(colander.String())
       age = colander.SchemaNode(colander.Int(),
                                 validator=colander.Range(0, 200))

If we try to serialize partial data using the ``serialize`` method of
the schema:
                                
.. code-block:: python
   :linenos:

     data = {'age':20, 'name':'Bob'}
     schema = Person()
     deserialized = schema.serialize(data)

The value for ``deserialized`` above will be ``{'age':'20',
'name':'Bob'}`` (note the integer has become a string).

Note that validation of values happens during serialization, just as
it does during deserialization.

Schema nodes also define a ``pserialize`` method, which can be used to
"partially" serialize data.  This is most useful when you want to
serialize a data structure where some of the values are missing.

For example, if we try to serialize partial data using the
``serialize`` method of the schema we defined above:
                                
.. code-block:: python
   :linenos:

     data = {'age':20}
     schema = Person()
     deserialized = schema.serialize(data)

When we attempt to invoke ``serialize``, an :exc:`colander.Invalid`
error will be raised, because we did not include the ``name``
attribute in our data.

To serialize with data representing only a part of the schema, use the
``pserialize`` method:

.. code-block:: python
   :linenos:

     data = {'age':20}
     schema = Person()
     deserialized = schema.pserialize(data)

No error is raised, and the value for ``deserialized`` above will be
``{'age':'20'}`` (note the integer has become a string).

A ``pdeserialize`` method also exists, which is a mirror image of
``pserialize`` for deserialization.

Defining A Schema Imperatively
------------------------------

The above schema we defined was defined declaratively via a set of
``class`` statements.  It's often useful to create schemas more
dynamically.  For this reason, Colander offers an "imperative" mode of
schema configuration.  Here's our previous declarative schema:

.. code-block:: python
   :linenos:

   import colander

   class Friend(colander.TupleSchema):
       rank = colander.SchemaNode(colander.Int(), 
                                 validator=colander.Range(0, 9999))
       name = colander.SchemaNode(colander.String())

   class Phone(colander.MappingSchema):
       location = colander.SchemaNode(colander.String(), 
                                     validator=colander.OneOf(['home', 'work']))
       number = colander.SchemaNode(colander.String())

   class Friends(colander.SequenceSchema):
       friend = Friend()

   class Phones(colander.SequenceSchema):
       phone = Phone()

   class Person(colander.MappingSchema):
       name = colander.SchemaNode(colander.String())
       age = colander.SchemaNode(colander.Int(),
                                validator=colander.Range(0, 200))
       friends = Friends()
       phones = Phones()

We can imperatively construct a completely equivalent schema like so:

.. code-block:: python
   :linenos:

   import colander

   friend = colander.SchemaNode(Tuple())
   friend.add(colander.SchemaNode(colander.Int(),
                                 validator=colander.Range(0, 9999),
              name='rank'))
   friend.add(colander.SchemaNode(colander.String()), name='name')

   phone = colander.SchemaNode(Mapping())
   phone.add(colander.SchemaNode(colander.String(),
                                validator=colander.OneOf(['home', 'work']),
                                name='location'))
   phone.add(colander.SchemaNode(colander.String(), name='number'))

   schema = colander.SchemaNode(Mapping())
   schema.add(colander.SchemaNode(colander.String(), name='name'))
   schema.add(colander.SchemaNode(colander.Int(), name='age'), 
                                 validator=colander.Range(0, 200))
   schema.add(colander.SchemaNode(colander.Sequence(), friend, name='friends'))
   schema.add(colander.SchemaNode(colander.Sequence(), phone, name='phones'))

Defining a schema imperatively is a lot uglier than defining a schema
declaratively, but it's often more useful when you need to define a
schema dynamically. Perhaps in the body of a function or method you
may need to disinclude a particular schema field based on a business
condition; when you define a schema imperatively, you have more
opportunity to control the schema composition.

Serializing and deserializing using a schema created imperatively is
done exactly the same way as you would serialize or deserialize using
a schema created declaratively:

.. code-block:: python
   :linenos:

     data = {
            'name':'keith',
            'age':'20',
            'friends':[('1', 'jim'),('2', 'bob'), ('3', 'joe'), ('4', 'fred')],
            'phones':[{'location':'home', 'number':'555-1212'},
                      {'location':'work', 'number':'555-8989'},],
            }
     deserialized = schema.deserialize(data)

Defining a New Type
-------------------

A new type is a class with two methods:: ``serialize`` and
``deserialize``.  ``serialize`` converts a Python data structure to a
serialization.  ``deserialize`` converts a value to a Python data
structure.

Here's a type which implements boolean serialization and
deserialization.  It serializes a boolean to the string ``true`` or
``false``; it deserializes a string (presumably ``true`` or ``false``,
but allows some wiggle room for ``t``, ``on``, ``yes``, ``y``, and
``1``) to a boolean value.

.. code-block::  python
   :linenos:

   class Boolean(object):
       def deserialize(self, node, value):
           if not isinstance(value, basestring):
               raise Invalid(node, '%r is not a string' % value)
           value = value.lower()
           if value in ('true', 'yes', 'y', 'on', 't', '1'):
               return True
           return False

       def serialize(self, node, value):
           if not isinstance(value, bool):
              raise Invalid(node, '%r is not a boolean')
           return value and 'true' or 'false'

       pdeserialize = deserialize
       pserialize = serialize

Here's how you would use the resulting class as part of a schema:

.. code-block:: python
   :linenos:

   import colander

   class Schema(colander.MappingSchema):
       interested = colander.SchemaNode(Boolean())

The above schema has a member named ``interested`` which will now be
serialized and deserialized as a boolean, according to the logic
defined in the ``Boolean`` type class.

Note that the only real constraint of a type class is that its
``serialize`` method must be able to make sense of a value generated
by its ``deserialize`` method and vice versa.

The serialize and deserialize methods of a type accept two values:
``node``, and ``value``.  ``node`` will be the schema node associated
with this type.  It is used when the type must raise a
:exc:`colander.Invalid` error, which expects a schema node as its
first constructor argument.  ``value`` will be the value that needs to
be serialized or deserialized.

``pdeserialize`` and ``pserialize`` methods are required on all types.
These are called to "partially" serialize a data structure.  For most
"leaf-level" types, partial serialization and deserialization does not
make any sense, so these methods are aliased to ``deserialize`` and
``serialize`` respectively.  However, for types representing mappings
or sequences, they may end up being different.

For a more formal definition of a the interface of a type, see
:class:`colander.interfaces.Type`.

Defining a New Validator
------------------------

A validator is a callable which accepts two positional arguments:
``node`` and ``value``.  It returns ``None`` if the value is valid.
It raises a :class:`colander.Invalid` exception if the value is not
valid.  Here's a validator that checks if the value is a valid credit
card number.

.. code-block:: python
   :linenos:

   def luhnok(node, value):
       """ checks to make sure that the value passes a luhn mod-10 checksum """
       sum = 0
       num_digits = len(value)
       oddeven = num_digits & 1

       for count in range(0, num_digits):
           digit = int(value[count])

           if not (( count & 1 ) ^ oddeven ):
               digit = digit * 2
           if digit > 9:
               digit = digit - 9

           sum = sum + digit

       if not (sum % 10) == 0:
           raise Invalid(node, 
                         '%r is not a valid credit card number' % value)
        
Here's how the resulting ``luhnok`` validator might be used in a
schema:

.. code-block:: python
   :linenos:

   import colander

   class Schema(colander.MappingSchema):
       cc_number = colander.SchemaNode(colander.String(), validator=lunhnok)

Note that the validator doesn't need to check if the ``value`` is a
string: this has already been done as the result of the type of the
``cc_number`` schema node being :class:`colander.String`. Validators
are always passed the *deserialized* value when they are invoked.

The ``node`` value passed to the validator is a schema node object; it
must in turn be passed to the :exc:`colander.Invalid` exception
constructor if one needs to be raised.

For a more formal definition of a the interface of a validator, see
:class:`colander.interfaces.Validator`.

Interface and API Documentation
-------------------------------

.. toctree::
   :maxdepth: 2

   interfaces.rst
   api.rst

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
