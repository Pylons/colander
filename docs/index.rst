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
       rank = colander.Structure(colander.Int(), 
                                 validator=colander.Range(0, 9999))
       name = colander.Structure(colander.String())

   class Phone(colander.MappingSchema):
       location = colander.Structure(colander.String(), 
                                     validator=colander.OneOf(['home', 'work']))
       number = colander.Structure(colander.String())

   class Person(colander.MappingSchema):
       name = colander.Structure(colander.String())
       age = colander.Structure(colander.Int(), 
                                validator=colander.Range(0, 200))
       friends = colander.Structure(colander.Sequence(Friend()))
       phones = colander.Structure(colander.Sequence(Phone()))
       
For ease of reading, we've actually defined *three* schemas above, but
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

Structure Objects
~~~~~~~~~~~~~~~~~

A schema is composed of one or more *structure* objects, usually in a
nested arrangement.  Each structure object has a required *type*, an
optional deserialization *validator*, an optional *default*, and a
slightly less optional *name*.

The *type* of a structure indicates its data type (such as
``colander.Int`` or ``colander.String``).

The *validator* of a structure is called after deserialization; it
makes sure the deserialized value matches a constraint.  An example of
such a validator is provided in the schema above:
``validator=colander.Range(0, 200)``.  A validator is not called after
serialization, only after deserialization.

The *default* of a structure indicates its default value if a value
for the structure is not found in the input data during serialization
and deserialization.  It should be the *deserialized* representation.
If a structure does not have a default, it is considered required.

The *name* of a structure appears in error reports.

The name of a structure that is introduced as a class-level attribute
of a ``colander.MappingSchema`` or ``colander.TupleSchema`` is its
class attribute name.  For example:

.. code-block:: python
   :linenos:

   import colander

   class Phone(colander.MappingSchema):
       location = colander.Structure(colander.String(), 
                                     validator=colander.OneOf(['home', 'work']))
       number = colander.Structure(colander.String())

The name of the structure defined via ``location =
colander.Structure(..)`` within the schema above is ``location``.

Schema Objects
~~~~~~~~~~~~~~

The result of creating an instance of a ``colander.MappingSchema`` or
``colander.TupleSchema`` object is also a *structure* object.

Instantiating a ``colander.MappingSchema`` creates a structure which
has a *type* value of ``colander.Mapping``.  Instantiating a
``colander.TupleSchema`` creates a structure which has a *type* value
of ``colander.Tuple``.

A structure defined by instantiating a ``colander.MappingSchema`` or a
``colander.TupleSchema`` usually has no validator, and has the empty
string as its name.

Deserializing A Data Structure Using a Schema
---------------------------------------------

Earlier we defined a schema:

.. code-block:: python
   :linenos:

   import colander

   class Friend(colander.TupleSchema):
       rank = colander.Structure(colander.Int(), 
                                 validator=colander.Range(0, 9999))
       name = colander.Structure(colander.String())

   class Phone(colander.MappingSchema):
       location = colander.Structure(colander.String(), 
                                     validator=colander.OneOf(['home', 'work']))
       number = colander.Structure(colander.String())

   class Person(colander.MappingSchema):
       name = colander.Structure(colander.String())
       age = colander.Structure(colander.Int(),
                                validator=colander.Range(0, 200))
       friends = colander.Structure(colander.Sequence(Friend()))
       phones = colander.Structure(colander.Sequence(Phone()))

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

Below, the ``data` structure has some problems.  The ``age`` is a
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
     try:
         schema.deserialize(data)
     except colander.Invalid, e:
         print e.asdict()

The ``deserialize`` method will raise an exception, and the ``except``
clause above will be invoked, causing ``e.asdict()`` to be printed.
This wil print:

.. code-block:: python
   :linenos:

   {'age':'-1 is less than minimum value 0',
    'friends.1.0':'"t" is not a number',
    'phones.0.location:'"bar" is not one of ["home", "work"]'}

The above error dictionary is telling us that:

- The top-level age variable failed validation.

- Bob's rank (the Friend tuple name ``bob``'s zeroth element) is not a
  valid number.

- The zeroth phone number has a bad location: it should be one of
  "home" or "work".

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
       rank = colander.Structure(colander.Int(),
                                 validator=colander.Range(0, 9999))
       name = colander.Structure(colander.String())

   class Phone(colander.MappingSchema):
       location = colander.Structure(colander.String(), 
                                     validator=colander.OneOf(['home', 'work']))
       number = colander.Structure(colander.String())

   class Person(colander.MappingSchema):
       name = colander.Structure(colander.String())
       age = colander.Structure(colander.Int(),
                                validator=colander.Range(0, 200))
       friends = colander.Structure(colander.Sequence(Friend()))
       phones = colander.Structure(colander.Sequence(Phone()))

We can imperatively construct a completely equivalent schema like so:

.. code-block:: python
   :linenos:

   import colander

   friend = colander.Structure(Tuple())
   friend.add(colander.Structure(colander.Int(),
                                 validator=colander.Range(0, 9999),
              name='rank'))
   friend.add(colander.Structure(colander.String()), name='name')

   phone = colander.Structure(Mapping())
   phone.add(colander.Structure(colander.String(),
                                validator=colander.OneOf(['home', 'work']),
                                name='location'))
   phone.add(colander.Structure(colander.String(), name='number'))

   schema = colander.Structure(Mapping())
   schema.add(colander.Structure(colander.String(), name='name'))
   schema.add(colander.Structure(colander.Int(), name='age'), 
                                 validator=colander.Range(0, 200))
   schema.add(colander.Structure(colander.Sequence(friend), name='friends'))
   schema.add(colander.Structure(colander.Sequence(phone), name='phones'))

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
       def deserialize(self, struct, value):
           if not isinstance(value, basestring):
               raise Invalid(struct, '%r is not a string' % value)
           value = value.lower()
           if value in ('true', 'yes', 'y', 'on', 't', '1'):
               return True
           return False

       def serialize(self, struct, value):
           if not isinstance(value, bool):
              raise Invalid(struct, '%r is not a boolean')
           return value and 'true' or 'false'

Here's how you would use the resulting class as part of a schema:

.. code-block:: python
   :linenos:

   import colander

   class Schema(colander.MappingSchema):
       interested = colander.Structure(Boolean())

The above schema has a member named ``interested`` which will now be
serialized and deserialized as a boolean, according to the logic
defined in the ``Boolean`` type class.

Note that the only real constraint of a type class is that its
``serialize`` method must be able to make sense of a value generated
by its ``deserialize`` method and vice versa.

For a more formal definition of a the interface of a type, see
:class:`colander.interfaces.Type`.

Defining a New Validator
------------------------

A validator is a callable which accepts two positional arguments:
``struct`` and ``value``.  It returns ``None`` if the value is valid.
It raises a ``colander.Invalid`` exception if the value is not valid.
Here's a validator that checks if the value is a valid credit card
number.

.. code-block:: python
   :linenos:

   def luhnok(struct, value):
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
           raise Invalid(struct, 
                         '%r is not a valid credit card number' % value)
        
Here's how the resulting ``luhnok`` validator might be used in a
schema:

.. code-block:: python
   :linenos:

   import colander

   class Schema(colander.MappingSchema):
       cc_number = colander.Structure(colander.String(), validator=lunhnok)

Note that the validator doesn't need to check if the ``value`` is a
string: this has already been done as the result of the type of the
``cc_number`` structure being ``colander.String``. Validators are
always passed the *deserialized* value when they are invoked.

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
