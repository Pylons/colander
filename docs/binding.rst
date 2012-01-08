Schema Binding
==============

.. note:: Schema binding is new in colander 0.8.

Sometimes, when you define a schema at module-scope using a ``class``
statement, you simply don't have enough information to provide
fully-resolved arguments to the :class:`colander.SchemaNode`
constructor.  For example, the ``validator`` of a schema node may
depend on a set of values that are only available within the scope of
some function that gets called much later in the process lifetime;
definitely some time very much later than module-scope import.

You needn't use schema binding at all to deal with this situation.
You can instead mutate a cloned schema object by changing its
attributes and assigning it values (such as widgets, validators, etc)
within the function which has access to the missing values
imperatively within the scope of that function.

However, if you'd prefer, you can use "deferred" values as SchemaNode
keyword arguments to a schema defined at module scope, and
subsequently use "schema binding" to resolve them later.  This can
make your schema seem "more declarative": it allows you to group all
the code that will be run when your schema is used together at module
scope.

What Is Schema Binding?
-----------------------

- Any values passed as a keyword argument to a SchemaNode
  (e.g. ``description``, ``missing``, etc.)  may be an instance of the
  ``colander.deferred`` class.  Instances of the ``colander.deferred`` class
  are callables which accept two positional arguments: a ``node`` and a
  ``kw`` dictionary.

- When a schema node is bound, it is cloned, and any ``colander.deferred``
  values it has as attributes will be resolved by invoking the callable
  represented by the deferred value.

- A ``colander.deferred`` value is a callable that accepts two
  positional arguments: the schema node being bound and a set of
  arbitrary keyword arguments.  It should return a value appropriate
  for its usage (a widget, a missing value, a validator, etc).

- Deferred values are not resolved until the schema is bound.

- Schemas are bound via the :meth:`colander.SchemaNode.bind` method.
  For example: ``someschema.bind(a=1, b=2)``.  The keyword values
  passed to ``bind`` are presented as the value ``kw`` to each
  ``colander.deferred`` value found.

- The schema is bound recursively.  Each of the schema node's children
  are also bound.

An Example
----------

Let's take a look at an example:

.. code-block:: python
   :linenos:

      import datetime
      import colander
      import deform

      @colander.deferred
      def deferred_date_validator(node, kw):
          max_date = kw.get('max_date')
          if max_date is None:
              max_date = datetime.date.today()
          return colander.Range(min=datetime.date.min, max=max_date)

      @colander.deferred
      def deferred_date_description(node, kw):
          max_date = kw.get('max_date')
          if max_date is None:
              max_date = datetime.date.today()
          return 'Blog post date (no earlier than %s)' % max_date.ctime()

      @colander.deferred
      def deferred_date_missing(node, kw):
          default_date = kw.get('default_date')
          if default_date is None:
              default_date = datetime.date.today()
          return default_date

      @colander.deferred
      def deferred_body_validator(node, kw):
          max_bodylen = kw.get('max_bodylen')
          if max_bodylen is None:
              max_bodylen = 1 << 18
          return colander.Length(max=max_bodylen)

      @colander.deferred
      def deferred_body_description(node, kw):
          max_bodylen = kw.get('max_bodylen')
          if max_bodylen is None:
              max_bodylen = 1 << 18
          return 'Blog post body (no longer than %s bytes)' % max_bodylen

      @colander.deferred
      def deferred_body_widget(node, kw):
          body_type = kw.get('body_type')
          if body_type == 'richtext':
              widget = deform.widget.RichTextWidget()
          else:
              widget = deform.widget.TextAreaWidget()
          return widget

      @colander.deferred
      def deferred_category_validator(node, kw):
          categories = kw.get('categories', [])
          return colander.OneOf([ x[0] for x in categories ])

      @colander.deferred
      def deferred_category_widget(node, kw):
          categories = kw.get('categories', [])
          return deform.widget.RadioChoiceWidget(values=categories)

      class BlogPostSchema(colander.Schema):
          title = colander.SchemaNode(
              colander.String(),
              title = 'Title',
              description = 'Blog post title',
              validator = colander.Length(min=5, max=100),
              widget = deform.widget.TextInputWidget(),
              )
          date = colander.SchemaNode(
              colander.Date(),
              title = 'Date',
              missing = deferred_date_missing,
              description = deferred_date_description,
              validator = deferred_date_validator,
              widget = deform.widget.DateInputWidget(),
              )
          body = colander.SchemaNode(
              colander.String(),
              title = 'Body',
              description = deferred_body_description,
              validator = deferred_body_validator,
              widget = deferred_body_widget,
              )
          category = colander.SchemaNode(
              colander.String(),
              title = 'Category',
              description = 'Blog post category',
              validator = deferred_category_validator,
              widget = deferred_category_widget,
              )
      
      schema = BlogPostSchema().bind(
          max_date = datetime.date.max,
          max_bodylen = 5000,
          body_type = 'richtext',
          default_date = datetime.date.today(),
          categories = [('one', 'One'), ('two', 'Two')]
          )

We use ``colander.deferred`` in its preferred manner here: as a
decorator to a function that takes two arguments.  For a schema node
value to be considered deferred, it must be an instance of
``colander.deferred`` and using that class as a decorator is the
easiest way to ensure that this happens.
        
To perform binding, the ``bind`` method of a schema node must be
called.  ``bind`` returns a *clone* of the schema node (and its
children, recursively), with all ``colander.deferred`` values
resolved.  In the above example:

-  The ``date`` node's ``missing`` value will be ``datetime.date.today()``.

- The ``date`` node's ``validator`` value will be a
  :class:`colander.Range` validator with a ``max`` of
  ``datetime.date.max``.

- The ``date`` node's ``widget`` will be of the type ``DateInputWidget``.

- The ``body`` node's ``description`` will be the string ``Blog post
  body (no longer than 5000 bytes)``.

- The ``body`` node's ``validator`` value will be a
  :class:`colander.Length` validator with a ``max`` of 5000.

- The ``body`` node's ``widget`` will be of the type ``RichTextWidget``.

- The ``category`` node's ``validator`` will be of the type
  :class:`colander.OneOf`, and its ``choices`` value will be ``['one',
  'two']``.

- The ``category`` node's ``widget`` will be of the type
  ``RadioChoiceWidget``, and the values it will be provided will be
  ``[('one', 'One'), ('two', 'Two')]``.

``after_bind``
--------------

Whenever a cloned schema node has had its values successfully bound,
it can optionally call an ``after_bind`` callback attached to itself.
This can be useful for adding and removing children from schema nodes:

.. code-block:: python
   :linenos:

      def maybe_remove_date(node, kw):
          if not kw.get('use_date'):
              del node['date']

      class BlogPostSchema(colander.Schema):
          title = colander.SchemaNode(
              colander.String(),
              title = 'Title',
              description = 'Blog post title',
              validator = colander.Length(min=5, max=100),
              widget = deform.widget.TextInputWidget(),
              )
          date = colander.SchemaNode(
              colander.Date(),
              title = 'Date',
              description = 'Date',
              widget = deform.widget.DateInputWidget(),
              )

       blog_schema = BlogPostSchema(after_bind=maybe_remove_date)
       blog_schema = blog_schema.bind(use_date=False)

An ``after_bind`` callback is called after a clone of this node has
bound all of its values successfully.  The above example removes the
``date`` node if the ``use_date`` keyword in the binding keyword
arguments is not true.

The deepest nodes in the node tree are bound first, so the
``after_bind`` methods of the deepest nodes are called before the
shallowest.

An ``after_bind`` callback should should accept two values: ``node``
and ``kw``.  ``node`` will be a clone of the bound node object, ``kw``
will be the set of keywords passed to the ``bind`` method.  It usually
operates on the ``node`` it is passed using the API methods described
in :class:`SchemaNode`.

Unbound Schemas With Deferreds
------------------------------

If you use a schema with deferred ``validator``, ``missing`` or
``default`` attributes, but you use it to perform serialization and
deserialization without calling its ``bind`` method:

- If ``validator`` is deferred, no validation will be performed.

- If ``missing`` is deferred, the field will be considered *required*.

- If ``default`` is deferred, the serialization default will be
  assumed to be ``colander.null``.

See Also
--------

See also the :meth:`colander.SchemaNode.bind` method and the
description of ``after_bind`` in the documentation of the
:class:`colander.SchemaNode` constructor.

