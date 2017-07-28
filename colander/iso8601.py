from __future__ import absolute_import

from datetime import timedelta, tzinfo
import iso8601
from iso8601.iso8601 import (ParseError, FixedOffset, UTC, ISO8601_REGEX)

try:
    from iso8601.iso8601 import Utc, ZERO, parse_date
except ImportError:
    from iso8601.iso8601 import parse_date as iso8601_parse_date
    # Yoinked from python docs
    ZERO = timedelta(0)

    class Utc(tzinfo):
        """UTC Timezone

        """
        def utcoffset(self, dt):
            return ZERO

        def tzname(self, dt):
            return "UTC"

        def dst(self, dt):
            return ZERO

        def __repr__(self):
            return "<iso8601.Utc>"

    UTC = Utc()
    iso8601.iso8601.UTC = UTC

    def parse_date(datestring, default_timezone=UTC):
        return iso8601_parse_date(
            datestring,
            default_timezone=default_timezone)

    class FixedOffset(tzinfo):
        """Fixed offset in hours and minutes from UTC

        """
        def __init__(self, offset_hours, offset_minutes, name):
            self.__offset_hours = offset_hours  # Keep for later __getinitargs__
            self.__offset_minutes = offset_minutes  # Keep for later __getinitargs__
            self.__offset = timedelta(hours=offset_hours, minutes=offset_minutes)
            self.__name = name

        def __eq__(self, other):
            if isinstance(other, FixedOffset):
                return (
                    (other.__offset == self.__offset)
                    and
                    (other.__name == self.__name)
                )
            if isinstance(other, tzinfo):
                return other == self
            return False

        def __getinitargs__(self):
            return (self.__offset_hours, self.__offset_minutes, self.__name)

        def utcoffset(self, dt):
            return self.__offset

        def tzname(self, dt):
            return self.__name

        def dst(self, dt):
            return ZERO

        def __repr__(self):
            return "<FixedOffset %r %r>" % (self.__name, self.__offset)


__all__ = ["parse_date", "ParseError", "Utc", "FixedOffset"]
