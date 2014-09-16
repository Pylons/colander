from __future__ import unicode_literals
import logging

from . import _SchemaMeta
from . import SchemaNode
from . import Mapping


logger = logging.getLogger(__name__)


def get_root_class(bases, super_cls):
    """Get root class which has super_cls in base classes

    """
    bases_set = set(bases)
    root_cls = None
    while root_cls is None and bases_set:
        next_bases_set = set()
        for base_cls in bases_set:
            if AbstractSchema in base_cls.__bases__:
                root_cls = base_cls
                break
            next_bases_set |= set(base_cls.__bases__)
        bases_set = next_bases_set
    return root_cls


class _AbstractMeta(_SchemaMeta):
    def __init__(cls, name, bases, clsattrs):
        def super_init():
            return super(_AbstractMeta, cls).__init__(name, bases, clsattrs)
        # AbstractSchema class, skip
        if bases == (SchemaNode, ):
            return super_init()
        # this class inherts Abstract as parent
        if AbstractSchema in bases:
            if '__mapper_args__' not in clsattrs:
                raise TypeError('__mapper_args__ should be defined')
            if 'polymorphic_on' not in clsattrs['__mapper_args__']:
                raise TypeError('__mapper_args__ should has polymorphic_on')
            cls.__polymorphic_mapping__ = {}
        else:
            # find the root class, for example:
            #     + AbstractSchema
            #         + root
            #             + foo
            #                 + bar
            # so the root class will be `root`
            root_cls = get_root_class(bases, AbstractSchema)
            # register this class to root class
            polymorphic_on = root_cls.__mapper_args__['polymorphic_on']
            polymorphic_id = clsattrs[polymorphic_on]
            if polymorphic_id in root_cls.__polymorphic_mapping__:
                raise KeyError('%s already exists' % polymorphic_id)
            root_cls.__polymorphic_mapping__[polymorphic_id] = cls

            logger.info(
                'Register class %s to root class %s as %s',
                cls, root_cls, polymorphic_id,
            )
        return super_init()


class Abstract(Mapping):

    def _get_subnode(self, node, data):
        polymorphic_on = node.__mapper_args__['polymorphic_on']
        polymorphic_id = data[polymorphic_on]
        root_cls = get_root_class((node.__class__, ), AbstractSchema)
        cls = root_cls.__polymorphic_mapping__[polymorphic_id]
        subnode = cls()
        return subnode

    def serialize(self, node, appstruct, not_abstract=False):
        if not_abstract:
            return super(Abstract, self).serialize(node, appstruct)
        subnode = self._get_subnode(node, appstruct)
        return subnode.typ.serialize(subnode, appstruct, not_abstract=True)

    def deserialize(self, node, cstruct, not_abstract=False):
        if not_abstract:
            return super(Abstract, self).deserialize(node, cstruct)
        subnode = self._get_subnode(node, cstruct)
        return subnode.typ.deserialize(subnode, cstruct, not_abstract=True)


class AbstractSchema(SchemaNode):
    __metaclass__ = _AbstractMeta
    schema_type = Abstract
