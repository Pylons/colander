Colander
========

Colander is useful as a system for validating and deserializing data
obtained via XML, JSON, an HTML form post or any other equally simple
data serialization.  Colander can be used to:

- Define a data schema.

- Deserialize a data structure composed of strings, mappings, and
  lists into an arbitrary Python structure after validating the data
  structure against a data schema.

- Serialize an arbitrary Python structure to a data structure composed
  of strings, mappings, and lists.

Colander is a good basis for form generation systems, data
description systems, and configuration systems.

Out of the box, Colander can serialize and deserialize various types
of objects, including:

- A mapping object (e.g. dictionary).

- A variable-length sequence of objects (each object is of the same
  type).

- A fixed-length tuple of objects (each object is of a different
  type).

- A string or Unicode object.

- An integer.

- A float.

- A decimal float.

- A boolean.

- An importable Python object (to a dotted Python object path).

- A Python ``datetime.datetime`` object.

- A Python ``datetime.date`` object.

Colander allows additional data structures to be serialized and
deserialized by allowing a developer to define new "types".

The error messages used by Colander's default types are
internationalizable.

.. toctree::
   :maxdepth: 2

   basics.rst
   null.rst
   extending.rst
   binding.rst
   manipulation.rst
   interfaces.rst
   api.rst
   glossary.rst
   changes.rst

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

