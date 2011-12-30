.. _basics:

Colander Basics
===============

Basics of using colander include defining a colander schema,
deserializing a data structure using a schema, serializing a data
structure using a schema, and dealing with :exc:`colander.Invalid`
exceptions.

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

A schema is composed of one or more *schema node* objects, each typically of
the class :class:`colander.SchemaNode`, usually in a nested arrangement.
Each schema node object has a required *type*, an optional *preparer*
for adjusting data after deserialization, an optional
*validator* for deserialized prepared data, an optional *default*, an
optional *missing*, an optional *title*, an optional *description*,
and a slightly less optional *name*.  It also accepts *arbitrary*
keyword arguments, which are attached directly as attributes to the
node instance.

The *type* of a schema node indicates its data type (such as
:class:`colander.Int` or :class:`colander.String`).

The *preparer* of a schema node is called after
deserialization but before validation; it prepares a deserialized
value for validation. Examples would be to prepend schemes that may be
missing on url values or to filter html provided by a rich text
editor. A preparer is not called during serialization, only during
deserialization.

The *validator* of a schema node is called after deserialization and
preparation ; it makes sure the value matches a constraint.  An example of
such a validator is provided in the schema above:
``validator=colander.Range(0, 200)``.  A validator is not called after
schema node serialization, only after node deserialization.

The *default* of a schema node indicates the value to be serialized if
a value for the schema node is not found in the input data during
serialization.  It should be the deserialized representation.  If a
schema node does not have a default, it is considered "serialization
required".

The *missing* of a schema node indicates the value if a value for the
schema node is not found in the input data during deserialization.  It
should be the deserialized representation.  If a schema node does not
have a default, it is considered "deserialization required".  This
value is never validated; it is considered pre-validated.

The *name* of a schema node appears in error reports.

The *title* of a schema node is metadata about a schema node that can
be used by higher-level systems.  By default, it is a capitalization
of the *name*.

The *description* of a schema node is metadata about a schema node
that can be used by higher-level systems.  By default, it is empty.

Any other keyword arguments to a schema node constructor will be
attached to the node unmolested (e.g. when ``foo=1`` is passed, the
resulting schema node will have an attribute named ``foo`` with the
value ``1``).

.. note:: You may see some higher-level systems (such as Deform) pass a
   ``widget`` argument to a SchemaNode constructor.  Such systems make use of
   the fact that a SchemaNode can be passed arbitrary keyword arguments for
   extension purposes.  ``widget`` and other keyword arguments not enumerated
   here but which are passed during schema node construction by someone
   constructing a schema for a particular purpose are not used internally by
   Colander; they are instead only meaningful to higher-level systems which
   consume Colander schemas.  Abitrary keyword arguments are allowed to a
   schema node constructor in Colander 0.9+.  Prior version disallow them.

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

Deserialization
---------------

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

Each of thse concrete data structures is called a :term:`cstruct`.
"cstruct" is an abbreviation of "colander structure": you can think of
a cstruct as a serialized representation of some application data.  A
"cstruct" is usually generated by the
:meth:`colander.SchemaNode.serialize` method, and is converted back
into an application structure (aka :term:`appstruct`) via
:meth:`colander.SchemaNode.deserialize`.

Deserializing A Valid Serialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python
   :linenos:

     cstruct = {
            'name':'keith',
            'age':'20',
            'friends':[('1', 'jim'),('2', 'bob'), ('3', 'joe'), ('4', 'fred')],
            'phones':[{'location':'home', 'number':'555-1212'},
                      {'location':'work', 'number':'555-8989'},],
            }
     schema = Person()
     deserialized = schema.deserialize(cstruct)

When ``schema.deserialize(cstruct)`` is called, because all the data in
the schema is valid, and the structure represented by ``cstruct``
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

Below, the ``cstruct`` structure has some problems.  The ``age`` is a
negative number.  The rank for ``bob`` is ``t`` which is not a valid
integer.  The ``location`` of the first phone is ``bar``, which is not
a valid location (it is not one of "work" or "home").  What happens
when a cstruct cannot be deserialized due to a data type error or a
validation error?

.. code-block:: python
   :linenos:

     import colander

     cstruct = {
            'name':'keith',
            'age':'-1',
            'friends':[('1', 'jim'),('t', 'bob'), ('3', 'joe'), ('4', 'fred')],
            'phones':[{'location':'bar', 'number':'555-1212'},
                      {'location':'work', 'number':'555-8989'},],
            }
     schema = Person()
     schema.deserialize(cstruct)

The ``deserialize`` method will raise an exception, and the ``except``
clause above will be invoked, causing an error message to be printed.
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

     cstruct = {
            'name':'keith',
            'age':'-1',
            'friends':[('1', 'jim'),('t', 'bob'), ('3', 'joe'), ('4', 'fred')],
            'phones':[{'location':'bar', 'number':'555-1212'},
                      {'location':'work', 'number':'555-8989'},],
            }
     schema = Person()
     try:
         schema.deserialize(cstruct)
     except colander.Invalid, e:
         errors = e.asdict()
         print errors

This will print something like:

.. code-block:: python
   :linenos:

   {'age':'-1 is less than minimum value 0',
    'friends.1.0':'"t" is not a number',
    'phones.0.location:'"bar" is not one of "home", "work"'}

:exc:`colander.Invalid` Exceptions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The exceptions raised by Colander during deserialization are instances
of the :exc:`colander.Invalid` exception class.  We saw previously
that instances of this exception class have a
:meth:`colander.Invalid.asdict` method which returns a dictionary of
error messages.  This dictionary is composed by Colander by walking
the *exception tree*.  The exception tree is composed entirely of
:exc:`colander.Invalid` exceptions.

While the :meth:`colander.Invalid.asdict` method is useful for simple
error reporting, a more complex application, such as a form library
that uses Colander as an underlying schema system, may need to do
error reporting in a different way.  In particular, such a system may
need to present the errors next to a field in a form. It may need to
translate error messages to another language.  To do these things
effectively, it will almost certainly need to walk and introspect the
exception graph manually. 

The :exc:`colander.Invalid` exceptions raised by Colander validation
are very rich.  They contain detailed information about the
circumstances of an error.  If you write a system based on Colander
that needs to display and format Colander exceptions specially, you
will need to get comfy with the Invalid exception API.  

When a validation-related error occurs during deserialization, each
node in the schema that had an error (and any of its parents) will be
represented by a corresponding :class:`colander.Invalid` exception.
To support this behavior, each :exc:`colander.Invalid` exception has a
``children`` attribute which is a list.  Each element in this list (if
any) will also be an :exc:`colander.Invalid` exception, recursively,
representing the error circumstances for a particular schema
deserialization.

Each exception in the graph has a ``msg`` attribute, which will either
be the value ``None``, a ``str`` or ``unicode`` object, or a
*translation string* instance representing a freeform error value set
by a particular type during an unsuccessful deserialization.
Exceptions that exist purely for structure will have a ``msg``
attribute with the value ``None``.  Each exception instance will also
have an attribute named ``node``, representing the schema node to
which the exception is related.

.. note:: Translation strings are objects which behave like Unicode objects
  but have extra metadata associated with them for use in translation
  systems.  See `http://docs.repoze.org/projects/translationstring/dev/
  <http://docs.pylonsproject.org/projects/translationstring/dev/>`_ for
  documentation about translation strings.  All error messages used by
  Colander internally are translation strings, which means they can be
  translated to other languages.  In particular, they are suitable for use as
  gettext *message ids*.

See the :class:`colander.Invalid` API documentation for more
information.

.. _preparing:

Preparing deserialized data for validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In certain circumstances, it is necessary to modify the deserialized
value before validating it.

For example, a :class:`~colander.String` node may be required to
contain content, but that content may come from a rich text
editor. Such an editor may return ``<b></b>`` which may appear to be
valid but doesn't contain content, or 
``<a href="javascript:alert('evil'')">good</a>`` which is valid, but
only after some processing.

The following schema uses `htmllaundry`__ and a
:class:`~colander.interfaces.Preparer` to do the correct thing in both
cases:

__ http://pypi.python.org/pypi/htmllaundry/

.. code-block:: python
   :linenos:

   import colander
   import htmllaundry

   class Page(colander.MappingSchema):
       title = colander.SchemaNode(colander.String())
       content = colander.SchemaNode(colander.String(),
                                     preparer=htmllaundry.sanitize,
                                     validator=colander.Length(1))


Serialization
-------------

Serializing a data structure is obviously the inverse operation from
deserializing a data structure.  The
:meth:`colander.SchemaNode.serialize` method of a schema performs
serialization of application data (aka an :term:`appstruct`).  If you
pass the :meth:`colander.SchemaNode.serialize` method data that can be
understood by the schema types in the schema you're calling it
against, you will be returned a data structure of serialized values.

For example, given the following schema:

.. code-block:: python
   :linenos:

   import colander

   class Person(colander.MappingSchema):
       name = colander.SchemaNode(colander.String())
       age = colander.SchemaNode(colander.Int(),
                                 validator=colander.Range(0, 200))

We can serialize a matching data structure:

.. code-block:: python
   :linenos:

     appstruct = {'age':20, 'name':'Bob'}
     schema = Person()
     serialized = schema.serialize(appstruct)

The value for ``serialized`` above will be ``{'age':'20',
'name':'Bob'}``.  Note that the ``age`` integer has become a string.

Serialization and deserialization are not completely symmetric,
however.  Although schema-driven data conversion happens during
serialization, and default values are injected as necessary,
:mod:`colander` types are defined in such a way that structural
validation and validation of values does *not* happen as it does
during deserialization.  For example, the :attr:`colander.null` value
is substituted into the cstruct for every missing subvalue in an
appstruct, and none of the validators associated with the schema or
any of is nodes is invoked.

This usually means you may "partially" serialize an appstruct where
some of the values are missing.  If we try to serialize partial data
using the ``serialize`` method of the schema:

.. code-block:: python
   :linenos:

     appstruct = {'age':20}
     schema = Person()
     serialized = schema.serialize(appstruct)

The value for ``serialized`` above will be ``{'age':'20',
'name':colander.null}``.  Note the ``age`` integer has become a
string, and the missing ``name`` attribute has been replaced with
:attr:`colander.null`.  Above, even though we did not include the
``name`` attribute in the appstruct we fed to ``serialize``, an error
is *not* raised.  For more information about :attr:`colander.null`
substitution during serialization, see :ref:`serializing_null`.

The corollary: it is the responsibility of the developer to ensure he
serializes "the right" data; :mod:`colander` will not raise an error
when asked to serialize something that is partially nonsense.

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

Gotchas
-------

You may be using a module scope schema definition with the expectation
that calling a :class:`colander.SchemaNode` constructor will clone all
of its subnodes.  This is not the case.

For example, in a Python module, you might have code that looks like this:

.. code-block:: python

   from colander import MappingSchema
   from colander import Int

   class MySchema1(MappingSchema):
       a = SchemaNode(Int())
   class MySchema2(MappingSchema):
       b = MySchema1()

   def afunction():
       s = MySchema2()
       s['a'].add(SchemaNode(Int(), name='c'))

Because you're mutating ``a`` (by appending a child node to it via the
:meth:`colander.SchemaNode.add` method) you are probably expecting
that you are working with a *copy* of ``a``.  This is incorrect:
you're mutating the module-scope copy of the ``a`` instance defined
within the ``MySchema1`` class.  This is almost certainly not what you
mean to do.  The symptom of making such a mistake might be that
multiple ``c`` nodes are added as children of ``a`` over the course of
the Python process lifetime.

To get around this, use the :meth:`colander.SchemaNode.clone` method
to create a deep copy of an instance of a schema otherwise defined at
module scope before mutating any of its subnodes:

.. code-block:: python

   def afunction():
       s = MySchema2().clone()
       s['a'].add(SchemaNode(Int(), name='c'))

:meth:`colander.SchemaNode.clone` clones all the nodes in the schema,
so you can work with a "deep copy" of the schema without disturbing the
"template" schema nodes defined at a higher scope.

