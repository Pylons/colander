.. _manipulating_data_structures:

Manipulating Data Structures
============================

Colander schemas have some utility functions which can be used to manipulate
an :term:`appstruct` or a :term:`cstruct`.  Nested data structures can be 
flattened into a single dictionary or a single flattened dictionary can be used 
to produce a nested data structure.  Values of particular nodes can also be set 
or retrieved based on a flattened path spec.

Flattening a Data Structure
---------------------------

:meth:`colander.SchemaNode.flatten` can be used to convert a datastructure with
nested dictionaries and/or lists into a single flattened dictionary where each
key in the dictionary is a dotted name path to the node in the nested structure.

Consider the following schema:

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

Consider also a particular serialization of data using that schema:

.. code-block:: python
   :linenos:

     appstruct = {
     'name':'keith',
     'age':20,
     'friends':[(1, 'jim'),(2, 'bob'), (3, 'joe'), (4, 'fred')],
     'phones':[{'location':'home', 'number':'555-1212'},
               {'location':'work', 'number':'555-8989'},],
     }

This data can be flattened:

.. code-block:: python
   :linenos:
     
     schema = Person()
     fstruct = schema.flatten(appstruct)

The resulting flattened structure would look like this:

.. code-block:: python
   :linenos:

     {
     'name': 'keith',
     'age': 20,
     'friends.0.rank': 1,
     'friends.0.name': 'jim',
     'friends.1.rank': 2,
     'friends.1.rank': 'bob',
     'friends.2.rank': 3,
     'friends.2.rank': 'joe',
     'friends.3.rank': 4,
     'friends.3.rank': 'fred',
     'phones.0.location': 'home',
     'phones.0.number': '555-1212',
     'phones.1.location': 'work',
     'phones.1.number': '555-8989',
     }

The process can be reversed using :meth:`colandar.SchemaNode.unflatten`:

.. code-block:: python
   :linenos:

     appstruct = schema.unflatten(fstruct)

Either an :term:`appstruct` or a :term:`cstruct` can be flattened or unflattened
in this way.

Accessing and Mutating Nodes in a Data Structure
------------------------------------------------

:attr:`colander.SchemaNode.get_value` and :attr:`colander.SchemaNode.set_value`
can be used to access and mutate nodes in an :term:`appstruct` or 
:term:`cstruct`. Using the example from above:

.. code-block:: python
   :linenos:

     # How much do I like Joe?
     rank = schema.get_value(appstruct, 'friends.2.rank')

     # Joe bought me beer. Let's promote Joe.
     schema.set_value(appstruct, 'friends.2.rank', rank + 5000)
