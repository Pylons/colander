# -*- coding:utf-8 -*-
import unittest
import datetime


class TestPolymorphism(unittest.TestCase):
    def _makeSchema(self, name='schema'):
        import colander
        from colander.polymorphism import AbstractSchema

        class Payload(AbstractSchema):
            cls_type = colander.SchemaNode(colander.String())
            __mapper_args__ = {
                'polymorphic_on': 'cls_type',
            }

        class Log(Payload):
            cls_type = 'log'
            message = colander.SchemaNode(colander.String())
            severity = colander.SchemaNode(colander.String(), validators=[
                colander.OneOf((
                    'debug',
                    'info',
                    'warning',
                    'error',
                ))
            ])

        class DatetimeLog(Log):
            cls_type = 'datetime-log'
            created_at = colander.SchemaNode(colander.DateTime())

        class Event(Payload):
            cls_type = 'event'
            tag = colander.SchemaNode(colander.String())
            data = colander.SchemaNode(colander.String())

        class MessageSchema(colander.MappingSchema):
            payload = Payload()

        schema = MessageSchema()
        return schema

    def test_serialize(self):
        from colander.iso8601 import Utc
        now = datetime.datetime.utcnow().replace(tzinfo=Utc())
        schema = self._makeSchema()

        result = schema.serialize({
            'payload': {
                'cls_type': 'log',
                'message': 'hello',
                'severity': 'info',
            }
        })
        self.assertEqual(result, {
            'payload': {
                'cls_type': 'log',
                'message': 'hello',
                'severity': 'info',
            }
        })

        result = schema.serialize({
            'payload': {
                'cls_type': 'datetime-log',
                'message': 'hello',
                'severity': 'info',
                'created_at': now,
            }
        })
        self.assertEqual(result, {
            'payload': {
                'cls_type': 'datetime-log',
                'message': 'hello',
                'severity': 'info',
                'created_at': now.isoformat(),
            }
        })

        result = schema.serialize({
            'payload': {
                'cls_type': 'event',
                'tag': 'foobar',
                'data': 'hi',
            }
        })
        self.assertEqual(result, {
            'payload': {
                'cls_type': 'event',
                'tag': 'foobar',
                'data': 'hi',
            }
        })

    def test_deserialize(self):
        from colander.iso8601 import Utc
        now = datetime.datetime.utcnow().replace(tzinfo=Utc())
        schema = self._makeSchema()
        result = schema.deserialize({
            'payload': {
                'cls_type': 'log',
                'message': 'hello',
                'severity': 'info',
            }
        })
        self.assertEqual(result, {
            'payload': {
                'cls_type': 'log',
                'message': 'hello',
                'severity': 'info',
            }
        })

        result = schema.deserialize({
            'payload': {
                'cls_type': 'datetime-log',
                'message': 'hello',
                'severity': 'info',
                'created_at': now.isoformat(),
            }
        })
        self.assertEqual(result, {
            'payload': {
                'cls_type': 'datetime-log',
                'message': 'hello',
                'severity': 'info',
                'created_at': now,
            }
        })

        result = schema.deserialize({
            'payload': {
                'cls_type': 'event',
                'tag': 'foobar',
                'data': 'hi',
            }
        })
        self.assertEqual(result, {
            'payload': {
                'cls_type': 'event',
                'tag': 'foobar',
                'data': 'hi',
            }
        })

    def test_not_exist_type(self):
        schema = self._makeSchema()
        with self.assertRaises(KeyError):
            schema.serialize({
                'payload': {
                    'cls_type': 'does_not_exist',
                    'message': 'hello',
                    'severity': 'info',
                }
            })
        with self.assertRaises(KeyError):
            schema.deserialize({
                'payload': {
                    'cls_type': 'does_not_exist',
                    'message': 'hello',
                    'severity': 'info',
                }
            })

    def test_duplicate_polymorphic_id(self):
        import colander
        from colander.polymorphism import AbstractSchema

        class Payload(AbstractSchema):
            cls_type = colander.SchemaNode(colander.String())
            __mapper_args__ = {
                'polymorphic_on': 'cls_type',
            }

        class Log(Payload):
            cls_type = 'log'

        with self.assertRaises(KeyError):
            class AnotherLog(Log):
                cls_type = 'log'
