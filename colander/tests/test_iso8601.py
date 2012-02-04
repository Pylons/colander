import unittest
import datetime

class Test_Utc(unittest.TestCase):
    def _makeOne(self):
        from ..iso8601 import Utc
        return Utc()

    def test_utcoffset(self):
        from ..iso8601 import ZERO
        inst = self._makeOne()
        result = inst.utcoffset(None)
        self.assertEqual(result, ZERO)

    def test_tzname(self):
        inst = self._makeOne()
        result = inst.tzname(None)
        self.assertEqual(result, "UTC")
        
    def test_dst(self):
        from ..iso8601 import ZERO
        inst = self._makeOne()
        result = inst.dst(None)
        self.assertEqual(result, ZERO)
        
class Test_FixedOffset(unittest.TestCase):
    def _makeOne(self):
        from ..iso8601 import FixedOffset
        return FixedOffset(1, 30, 'oneandahalf')

    def test_utcoffset(self):
        inst = self._makeOne()
        result = inst.utcoffset(None)
        self.assertEqual(result, datetime.timedelta(hours=1, minutes=30))

    def test_tzname(self):
        inst = self._makeOne()
        result = inst.tzname(None)
        self.assertEqual(result, 'oneandahalf')

    def test_dst(self):
        from ..iso8601 import ZERO
        inst = self._makeOne()
        result = inst.dst(None)
        self.assertEqual(result, ZERO)

    def test___repr__(self):
        inst = self._makeOne()
        result = inst.__repr__()
        self.assertEqual(result, "<FixedOffset 'oneandahalf'>")

class Test_parse_timezone(unittest.TestCase):
    def _callFUT(self, tzstring):
        from ..iso8601 import parse_timezone
        return parse_timezone(tzstring)

    def test_default_Z(self):
        from ..iso8601 import UTC
        result = self._callFUT('Z')
        self.assertEqual(result, UTC)

    def test_default_None(self):
        from ..iso8601 import UTC
        result = self._callFUT(None)
        self.assertEqual(result, UTC)

    def test_positive(self):
        tzstring = "+01:00"
        result = self._callFUT(tzstring)
        self.assertEqual(result.utcoffset(None), 
                         datetime.timedelta(hours=1, minutes=0))

    def test_negative(self):
        tzstring = "-01:00"
        result = self._callFUT(tzstring)
        self.assertEqual(result.utcoffset(None), 
                         datetime.timedelta(hours=-1, minutes=0))
        
class Test_parse_date(unittest.TestCase):
    def _callFUT(self, datestring):
        from ..iso8601 import parse_date
        return parse_date(datestring)

    def test_notastring(self):
        from ..iso8601 import ParseError
        self.assertRaises(ParseError, self._callFUT, None)

    def test_cantparse(self):
        from ..iso8601 import ParseError
        self.assertRaises(ParseError, self._callFUT, 'garbage')

    def test_normal(self):
        from ..iso8601 import UTC
        result = self._callFUT("2007-01-25T12:00:00Z")
        self.assertEqual(result, 
                         datetime.datetime(2007, 1, 25, 12, 0, tzinfo=UTC))
        
    def test_fraction(self):
        from ..iso8601 import UTC
        result = self._callFUT("2007-01-25T12:00:00.123Z")
        self.assertEqual(result, 
                         datetime.datetime(2007, 1, 25, 12, 0, 0, 123000,
                                           tzinfo=UTC))
        
