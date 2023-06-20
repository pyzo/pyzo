import re as _re


def parse_version_crudely(version_string):
    """extracts the leading number parts of a version string to a tuple
    e.g.: "123.45ew6.7x.dev8" --> (123, 45, 7)
    """
    return tuple(int(s) for s in _re.findall(r"\.(\d+)", "." + version_string))
