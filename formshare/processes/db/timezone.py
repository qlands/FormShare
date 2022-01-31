from formshare.models import TimeZone, map_from_schema

__all__ = [
    "get_timezone_offset",
    "get_timezones",
    "get_timezone_name",
    "timezone_exists",
]


def timezone_exists(request, timezone_code):
    res = (
        request.dbsession.query(TimeZone.timezone_utc_offset)
        .filter(TimeZone.timezone_code == timezone_code)
        .first()
    )
    if res is None:
        return False
    return True


def get_timezone_offset(request, timezone_code):
    res = (
        request.dbsession.query(TimeZone.timezone_utc_offset)
        .filter(TimeZone.timezone_code == timezone_code)
        .first()
    )
    return res[0]


def get_timezone_name(request, timezone_code):
    res = (
        request.dbsession.query(TimeZone.timezone_name)
        .filter(TimeZone.timezone_code == timezone_code)
        .first()
    )
    return res[0]


def get_timezones(request):
    res = request.dbsession.query(TimeZone).all()
    return map_from_schema(res)
