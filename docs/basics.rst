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
deserialization. You can also pass a schema node a list of preparers.

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

The *schema_order* of a schema node is an integer which defines its ultimate
order position within its parent node.  It is not useful unless a mapping
schema is inherited from another mapping schema, and you need to control the
ordering of the resulting nodes.

Any other keyword arguments to a schema node constructor will be
attached to the node unmolested (e.g. when ``foo=1`` is passed, the
resulting schema node will have an attribute named ``foo`` with the
value ``1``).

.. note::

   You may see some higher-level systems (such as Deform) pass a ``widget``
   argument to a SchemaNode constructor.  Such systems make use of the fact
   that a SchemaNode can be passed arbitrary keyword arguments for extension
   purposes.  ``widget`` and other keyword arguments not enumerated here but
   which are passed during schema node construction by someone constructing a
   schema for a particular purpose are not used internally by Colander; they
   are instead only meaningful to higher-level systems which consume Colander
   schemas.  Abitrary keyword arguments are allowed to a schema node
   constructor in Colander 0.9+.  Prior version disallow them.

Subclassing SchemaNode
++++++++++++++++++++++

As of Colander 1.0a1+, it is possible and advisable to subclass
:class:`colander.SchemaNode` in order to create a bundle of default node
behavior.  The subclass can define the following methods and attributes:
``preparer``, ``validator``, ``default``, ``missing``, ``name``, ``title``,
``description``, ``widget``, and ``after_bind``.

The imperative style that looks like this still works, of course:

.. code-block:: python

     from colander import SchemaNode

     ranged_int = colander.SchemaNode(
         validator=colander.Range(0, 10),
         default = 10,
         title='Ranged Int'
         )

But in 1.0a1+, you can alternately now do something like this:

.. code-block:: python

     from colander import SchemaNode

     class RangedIntSchemaNode(SchemaNode):
         validator = colander.Range(0, 10)
         default = 10
         title = 'Ranged Int'

     ranged_int = RangedInt()

Values that are expected to be callables can now alternately be methods of
the schemanode subclass instead of plain attributes:

.. code-block:: python

     from colander import SchemaNode

     class RangedIntSchemaNode(SchemaNode):
         default = 10
         title = 'Ranged Int'

         def validator(self, node, cstruct):
            if not 0 < cstruct < 10:
                raise colander.Invalid(node, 'Must be between 0 and 10')

     ranged_int = RangedInt()

Note that when implementing a method value such as ``validator`` that expects
to receive a ``node`` argument, ``node`` must be provided in the call
signature, even though ``node`` will almost always be the same as ``self``.
This is because Colander simply treats the method as another kind of
callable, be it a method, or a function, or an instance that has a
``__call__`` method.  It doesn't care that it happens to be a method of
``self``, and it needs to support callables that are not methods, so it sends
``node`` in regardless.

You can't use *method* definitions as ``colander.deferred`` callables.  For
example this will *not* work:

.. code-block:: python

     from colander import SchemaNode

     class RangedIntSchemaNode(SchemaNode):
         default = 10
         title = 'Ranged Int'

         @colander.deferred
         def validator(self, node, kw):
            request = kw['request']
            def avalidator(node, cstruct):
                if not 0 < cstruct < 10:
                    if request.user != 'admin':
                        raise colander.Invalid(node, 'Must be between 0 and 10')
            return avalidator

     ranged_int = RangedInt()
     bound_ranged_int = ranged_int.bind(request=request)

This will result in::

        TypeError: avalidator() takes exactly 3 arguments (2 given)

However, if you treat the thing being decorated as a function instead of a
method (remove the ``self`` argument from the argument list), it will
indeed work):

.. code-block:: python

     from colander import SchemaNode

     class RangedIntSchemaNode(SchemaNode):
         default = 10
         title = 'Ranged Int'

         @colander.deferred
         def validator(node, kw):
            request = kw['request']
            def avalidator(node, cstruct):
                if not 0 < cstruct < 10:
                    if request.user != 'admin':
                        raise colander.Invalid(node, 'Must be between 0 and 10')
            return avalidator

     ranged_int = RangedInt()
     bound_ranged_int = ranged_int.bind(request=request)

In releases of Colander before 1.0a1+, the only way to defer the computation of
values was via the ``colander.deferred`` decorator.  In this release, however,
you can instead use the ``bindings`` attribute of ``self`` to obtain access to
the bind parameters within values that are plain old methods:

.. code-block:: python

     from colander import SchemaNode

     class RangedIntSchemaNode(SchemaNode):
         default = 10
         title = 'Ranged Int'

         def validator(self, node, cstruct):
            request = self.bindings['request']
            if not 0 < cstruct < 10:
                if request.user != 'admin':
                    raise colander.Invalid(node, 'Must be between 0 and 10')

     ranged_int = RangedInt()
     bound_range_int = ranged_int.bind(request=request)

If the things you're trying to defer aren't callables like ``validator``, but
they're instead just plain attributes like ``missing`` or ``default``,
instead of using a ``colander.deferred``, you can use ``after_bind`` to set
attributes of the schemanode that rely on binding variables:

.. code-block:: python

     from colander import SchemaNode

     class UserIdSchemaNode(SchemaNode):
         title = 'User Id'

         def after_bind(self, node, kw):
             self.default = kw['request'].user.id

You can override the default values of a schemanode subclass in its
constructor:

.. code-block:: python

     from colander import SchemaNode

     class RangedIntSchemaNode(SchemaNode):
         default = 10
         title = 'Ranged Int'
         validator = colander.Range(0, 10)

     ranged_int = RangedInt(validator=colander.Range(0, 20))

In the above example, the validation will be done on 0-20, not 0-10.

Normal inheritance rules apply to class attributes and methods defined in a
schemanode subclass.  If your schemanode subclass inherits from another
schemanode class, your schemanode subclass' methods and class attributes will
override the superclass' methods and class attributes.

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

.. note::

  Translation strings are objects which behave like Unicode objects but have
  extra metadata associated with them for use in translation systems.  See
  `http://docs.repoze.org/projects/translationstring/dev/
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

You can even specify multiple preparers to be run in order, by passing
a list of functions to the `preparer` kwarg, like so:

.. code-block:: python
   :linenos:

   import colander
   # removes whitespace, newlines, and tabs from the beginning/end of a string
   strip_whitespace = lambda v: v.strip(' \t\n\r') if v is not None else v
   # replaces multiple spaces with a single space
   remove_multiple_spaces = lambda v: re.sub(' +', ' ', v)

   class Page(colander.MappingSchema):
       title = colander.SchemaNode(colander.String())
       content = colander.SchemaNode(colander.String(),
                                     preparer=[strip_whitespace, remove_multiple_spaces],
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

Inheriting Schemas
------------------

.. note::

   This feature is new as of Colander 0.9.9.

One class-based schema can be inherited from another.  For example:

.. code-block:: python

   import colander
   import pprint

   class Friend(colander.MappingSchema):
       rank = colander.SchemaNode(
           colander.Int(),
           )
       name = colander.SchemaNode(
           colander.String(),
           )

   class SpecialFriend(Friend):
       iwannacomefirst = colander.SchemaNode(
           colander.String(),
           insert_before='rank',
           )
       another = colander.SchemaNode(
           colander.String(),
           )

   class SuperSpecialFriend(SpecialFriend):
       iwannacomefirst = colander.SchemaNode(
           colander.Int(),
           )

   friend = SuperSpecialFriend()
   pprint.pprint([(x, x.typ) for x in friend.children])

Here's what's printed when the above is run:

.. code-block:: text

   [(<colander.SchemaNode object at 38407568 (named iwannacomefirst)>,
     <colander.Integer object at 0x24a0d10>),
    (<colander.SchemaNode object at 37016144 (named rank)>,
     <colander.Integer object at 0x7f17c5606710>),
    (<colander.SchemaNode object at 37017424 (named name)>,
     <colander.String object at 0x234d610>),
    (<colander.SchemaNode object at 38407184 (named another)>,
     <colander.String object at 0x2359250>)]

Multiple inheritance also works:

.. code-block:: python

   import colander
   import pprint

   class One(colander.MappingSchema):
       a = colander.SchemaNode(
           colander.Int(),
           )
       b = colander.SchemaNode(
           colander.Int(),
           )

   class Two(colander.MappingSchema):
       a = colander.SchemaNode(
           colander.String(),
           )
       c = colander.SchemaNode(
           colander.String(),
           )

   class Three(One, Two):
       b = colander.SchemaNode(
           colander.Bool(),
           )
       d = colander.SchemaNode(
           colander.Bool(),
           )

   s = Three()
   pprint.pprint([(x, x.typ) for x in s.children])

Here's what's printed when the above is run:

.. code-block:: text

   [(<colander.SchemaNode object at 14868560 (named a)>,
     <colander.String object at 0xe25f90>),
    (<colander.SchemaNode object at 14868816 (named b)>,
     <colander.Boolean object at 0xe2e110>),
    (<colander.SchemaNode object at 14868688 (named c)>,
     <colander.String object at 0xe2e090>),
    (<colander.SchemaNode object at 14868944 (named d)>,
     <colander.Boolean object at 0xe2e190>)]

This feature only works with mapping schemas.  A "mapping schema" is schema
defined as a class which inherits from :class:`colander.Schema` or
:class:`colander.MappingSchema`.

Ordering of child schema nodes when inheritance is used works like this: the
"deepest" SchemaNode class in the MRO of the inheritance chain is consulted
first for nodes, then the next deepest, then the next, and so on.  So the
deepest class' nodes come first in the relative ordering of schema nodes,
then the next deepest, and so on.  For example:

.. code-block:: python

      class One(colander.MappingSchema):
          a = colander.SchemaNode(
              colander.String(),
              id='a1',
              )
          b = colander.SchemaNode(
              colander.String(),
              id='b1',
              )
          d = colander.SchemaNode(
              colander.String(),
              id='d1',
              )

      class Two(One):
          a = colander.SchemaNode(
              colander.String(),
              id='a2',
              )
          c = colander.SchemaNode(
              colander.String(), 
              id='c2',
              )
          e = colander.SchemaNode(
              colander.String(),
              id='e2',
              )

      class Three(Two):
          b = colander.SchemaNode(
              colander.String(),
              id='b3',
              )
          d = colander.SchemaNode(
              colander.String(),
              id='d3',
              )
          f = colander.SchemaNode(
              colander.String(),
              id='f3',
              )

      three = Three()

The ordering of child nodes computed in the schema node ``three`` will be
``['a2', 'b3', 'd3', 'c2', 'e2', 'f3']``.  The ordering starts ``a1``,
``b1``, ``d1`` because that's the ordering of nodes in ``One``, and ``One``
is the deepest SchemaNode in the inheritance hierarchy.  Then it processes
the nodes attached to ``Two``, the next deepest, which causes ``a1`` to be
replaced by ``a2``, and ``c2`` and ``e2`` to be appended to the node list.
Then finally it processes the nodes attached to ``Three``, which causes
``b1`` to be replaced by ``b3``, and ``d1`` to be replaced by ``d3``, then
finally ``f`` is appended.

Multiple inheritance works the same way:

.. code-block:: python

      class One(colander.MappingSchema):
          a = colander.SchemaNode(
              colander.String(),
              id='a1',
              )
          b = colander.SchemaNode(
              colander.String(),
              id='b1',
              )
          d = colander.SchemaNode(
              colander.String(),
              id='d1',
              )

      class Two(colander.MappingSchema):
          a = colander.SchemaNode(
              colander.String(),
              id='a2',
              )
          c = colander.SchemaNode(
              colander.String(), 
              id='c2',
              )
          e = colander.SchemaNode(
              colander.String(),
              id='e2',
              )

      class Three(Two, One):
          b = colander.SchemaNode(
              colander.String(),
              id='b3',
              )
          d = colander.SchemaNode(
              colander.String(),
              id='d3',
              )
          f = colander.SchemaNode(
              colander.String(),
              id='f3',
              )

      three = Three()

The resulting node ordering of ``three`` is the same as the single
inheritance example: ``['a2', 'b3', 'd3', 'c2', 'e2', 'f3']`` due to the
MRO deepest-first ordering (``One``, then ``Two``, then ``Three``).

The behavior of subclassing one mapping schema using another is as follows:

* A node declared in a subclass of a mapping schema overrides any node with
  the same name inherited from any superclass.  The node remains at the child
  order of the superclass node unless the subclass node defines an
  ``insert_before`` value.

* A node declared in a subclass of a mapping schema with a name that doesn't
  override any node in a superclass will be placed *after* all nodes defined
  in all superclasses unless the subclass node defines an ``insert_before``
  value.  You can think of it like this: nodes added in subclasses will
  *follow* nodes added in superclasses unless the node is already defined in
  any of those superclasses.

An ``insert_before`` keyword argument may be passed to the SchemaNode
constructor of mapping schema child nodes.  This is a string which influences
the node's position in its mapping schema.  The node will be inserted into
the mapping schema before the node named by ``insert_before``.  An
``insert_before`` value must match the name of a schema node in a superclass
or it must match the name of a schema node already defined in the class; it
cannot name a schema node in a subclass, and it cannot name a schema node in
the same class that hasn't already been defined.  If an ``insert_before`` is
provided that doesn't match any existing node name, a :exc:`KeyError` is
raised.

If a schema node name conflicts with a schema value attribute name on the
same class in a :class:`colander.MappingSchema`,
:class:`colander.TupleSchema` or :class:`colander.SequenceSchema` definition,
you can work around this by giving the schema node a bogus name in the class
definition but providing a correct ``name`` argument to the schema node
constructor:

.. code-block:: python

     from colander import SchemaNode, MappingSchema

     class SomeSchema(MappingSchema):
         title = 'Some Schema'
         thisnamewillbeignored = colander.SchemaNode(
                                             colander.String(),
                                             name='title'
                                             )

Note that such a workaround is only required if the conflicting names are
attached to the *exact same* class definition.  Colander scrapes off schema
node definitions at each class' construction time, so it's not an issue for
inherited values.  For example:

.. code-block:: python

     from colander import SchemaNode, MappingSchema

     class SomeSchema(MappingSchema):
         title = colander.SchemaNode(colander.String())

     class AnotherSchema(SomeSchema):
         title = 'Some Schema'

     schema = AnotherSchema()

In the above example, even though the ``title = 'Some Schema'`` appears to
override the superclass' ``title`` SchemaNode, a ``title`` SchemaNode will
indeed be present in the child list of the ``schema`` instance
(``schema['title']`` will return the ``title`` SchemaNode) and the schema's
``title`` attribute will be ``Some Schema`` (``schema.title`` will return
``Some Schema``).


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

