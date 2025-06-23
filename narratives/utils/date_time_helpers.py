from datetime import datetime
import pytz

def normalize_to_utc(raw_dt_str: str, source_timezone_str: str = "UTC") -> datetime:
    """
    Normalizes any incoming datetime string into UTC.

    1️⃣ If input is ISO8601 with timezone offset → trusts the offset.
    2️⃣ If input is naive → applies source timezone.
    3️⃣ Always returns UTC-aware datetime object.

    :param raw_dt_str: incoming datetime string
    :param source_timezone_str: timezone of the source (if naive)
    :return: UTC datetime object
    """
    try:
        # First parse ISO8601 string
        dt = datetime.fromisoformat(raw_dt_str)

        if dt.tzinfo is None:
            # Naive timestamp — apply source timezone
            source_tz = pytz.timezone(source_timezone_str)
            localized = source_tz.localize(dt)
            return localized.astimezone(pytz.UTC)
        else:
            # Already timezone-aware → safely convert to UTC
            return dt.astimezone(pytz.UTC)

    except Exception as e:
        raise ValueError(f"Failed to parse timestamp '{raw_dt_str}': {e}")
