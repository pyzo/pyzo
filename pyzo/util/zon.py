# Copyright (C) 2016, Almar Klein

"""
Reading and saving Zoof Object Notation files. ZON is like JSON, but a
more Pythonic format. It's just about 500 lines of code.

This format is a spin-off from the SSDF format, it is fully compatible,
except that ZON does not support numpy arrays.
"""

import re
import sys
import time


## Dict class

from collections import OrderedDict as _dict


def isidentifier(s):
    return isinstance(s, str) and s.isidentifier()


class Dict(_dict):
    """A dict in which the items can be get/set as attributes."""

    __reserved_names__ = dir(_dict())  # Also from OrderedDict
    __pure_names__ = dir(dict())

    __slots__ = []

    def __repr__(self):
        identifier_items = []
        nonidentifier_items = []
        for key, val in self.items():
            if isidentifier(key):
                identifier_items.append("{}={!r}".format(key, val))
            else:
                nonidentifier_items.append("({!r}, {!r})".format(key, val))
        if nonidentifier_items:
            return "Dict([{}], {})".format(
                ", ".join(nonidentifier_items),
                ", ".join(identifier_items),
            )
        else:
            return "Dict({})".format(", ".join(identifier_items))

    def __getattribute__(self, key):
        try:
            return object.__getattribute__(self, key)
        except AttributeError:
            if key in self:
                return self[key]
            else:
                raise

    def __setattr__(self, key, val):
        if key in Dict.__reserved_names__:
            # Either let OrderedDict do its work, or disallow
            if key not in Dict.__pure_names__:
                return _dict.__setattr__(self, key, val)
            else:
                raise AttributeError(
                    "Reserved name, this key can only "
                    "be set via ``d[{!r}] = X``".format(key)
                )
        else:
            # if isinstance(val, dict): val = Dict(val) -> no, makes a copy!
            self[key] = val

    def __dir__(self):
        names = [k for k in self.keys() if isidentifier(k)]
        return Dict.__reserved_names__ + names


# SSDF compatibility
Struct = Dict
Struct.__is_ssdf_struct__ = True


## Public functions


def isstruct(ob):  # SSDF compatibility
    """Returns whether the given object is an SSDF struct."""
    return getattr(ob, "__is_ssdf_struct__", False)


def new():
    """Create a new Dict object. The same as "Dict()"."""
    return Dict()


def clear(d):  # SSDF compatibility
    """Clear all elements of the given Dict object."""
    d.clear()


def copy(object):
    """Return a deep copy the given object.

    The object and its children should be dict-compatible data types.
    Note that dicts are converted to Dict and tuples to lists.
    """
    if isstruct(object) or isinstance(object, dict):
        newObject = Dict()
        for key in object:
            val = object[key]
            newObject[key] = copy(val)
        return newObject
    elif isinstance(object, (tuple, list)):
        return [copy(ob) for ob in object]
    else:
        return object  # immutable


def count(object, cache=None):
    """Count the number of elements in the given object.

    An element is defined as one of the 6 datatypes supported
    by ZON (dict, tuple/list, string, int, float, None).
    """
    cache = cache or []
    if isstruct(object) or isinstance(object, (dict, list)):
        if id(object) in cache:
            raise RuntimeError("recursion!")
        cache.append(id(object))
    n = 1
    if isstruct(object) or isinstance(object, dict):
        for key in object:
            val = object[key]
            n += count(val, cache)
    elif isinstance(object, (tuple, list)):
        for val in object:
            n += count(val, cache)
    return n


def loads(text):
    """Load a Dict from the given string in ZON syntax."""
    if not isinstance(text, str):
        raise ValueError("zon.loads() expects a string.")
    reader = ReaderWriter()
    return reader.read(text)


def load(file):
    """Load a Dict from the given file or filename."""
    if isinstance(file, str):
        with open(file, "rb") as fd:
            data = fd.read()
    else:
        data = file.read()
    return loads(data.decode("utf-8"))


def saves(d):
    """Serialize the given dict to a string."""
    if not (isstruct(d) or isinstance(d, dict)):
        raise ValueError("ssdf.saves() expects a dict.")
    writer = ReaderWriter()
    text = writer.save(d)
    return text


def save(file, d):
    """Serialize the given dict to the given file or filename."""
    text = saves(d)
    if isinstance(file, str):
        file = open(file, "wb")
    with file:
        file.write(text.encode("utf-8"))


## The core


class ReaderWriter:
    def read(self, text):
        indent = 0
        root = Dict()
        container_stack = [(0, root)]
        new_container = None

        for i, line in enumerate(text.splitlines()):
            linenr = i + 1

            # Strip line
            line2 = line.lstrip()

            # Skip comments and empty lines
            if not line2 or line2[0] == "#":
                continue

            # Find the indentation
            prev_indent = indent
            indent = len(line) - len(line2)
            if indent == prev_indent:
                pass
            elif indent < prev_indent:
                while container_stack[-1][0] > indent:
                    container_stack.pop(-1)
                if container_stack[-1][0] != indent:
                    print("ZON: Ignoring wrong dedentation at {}".format(linenr))
            elif indent > prev_indent and new_container is not None:
                container_stack.append((indent, new_container))
                new_container = None
            else:
                print("ZON: Ignoring wrong indentation at {}".format(linenr))
                indent = prev_indent

            # Split name and data using a regular expression
            m = re.search(r"^\w+? *?=", line2)
            if m:
                i = m.end(0)
                name = line2[: i - 1].strip()
                data = line2[i:].lstrip()
            else:
                name = None
                data = line2

            # Get value
            value = self.to_object(data, linenr)

            # Store the value
            _indent, current_container = container_stack[-1]
            if isinstance(current_container, dict):
                if name:
                    current_container[name] = value
                else:
                    print("ZON: unnamed item in dict on line {}".format(linenr))
            elif isinstance(current_container, list):
                if name:
                    print("ZON: named item in list on line {}".format(linenr))
                else:
                    current_container.append(value)
            else:
                raise RuntimeError("Invalid container {!r}".format(current_container))

            # Prepare for next round
            if isinstance(value, (dict, list)):
                new_container = value

        return root

    def save(self, d):
        pyver = "{}.{}.{}".format(*sys.version_info[:3])
        ct = time.asctime()
        lines = [
            "# -*- coding: utf-8 -*-",
            "# This Zoof Object Notation (ZON) file was",
            "# created from Python {} on {}.\n".format(pyver, ct),
            "",
        ]
        lines.extend(self.from_dict(d, -2)[1:])

        return "\r\n".join(lines)
        # todo: pop toplevel dict

    def from_object(self, name, value, indent):
        # Get object's data
        if value is None:
            data = "Null"
        elif isinstance(value, int):
            data = self.from_int(value)
        elif isinstance(value, float):
            data = self.from_float(value)
        elif isinstance(value, bool):
            data = self.from_int(int(value))
        elif isinstance(value, str):
            data = self.from_unicode(value)
        elif isinstance(value, dict):
            data = self.from_dict(value, indent)
        elif isinstance(value, (list, tuple)):
            data = self.from_list(value, indent)
        else:
            # We do not know
            data = "Null"
            tmp = repr(value)
            if len(tmp) > 64:
                tmp = tmp[:64] + "..."
            if name is not None:
                print("ZON: {} is unknown object: {}".format(name, tmp))
            else:
                print("ZON: unknown object: {}".format(tmp))

        # Finish line (or first line)
        if isinstance(data, str):
            data = [data]
        if name:
            data[0] = "{}{} = {}".format(" " * indent, name, data[0])
        else:
            data[0] = "{}{}".format(" " * indent, data[0])

        return data

    def to_object(self, data, linenr):
        data = data.lstrip()

        # Determine what type of object we're dealing with by reading
        # like a human.
        if not data:
            print("ZON: no value specified at line {}.".format(linenr))
        elif data[0] in "-.0123456789":
            return self.to_int_or_float(data, linenr)
        elif data[0] == "'":
            return self.to_unicode(data, linenr)
        elif data.startswith("dict:"):
            return self.to_dict(data, linenr)
        elif data.startswith("list:") or data[0] == "[":
            return self.to_list(data, linenr)
        elif data.startswith(("Null", "None")):
            return None
        else:
            print("ZON: invalid type on line {}.".format(linenr))
            return None

    def to_int_or_float(self, data, linenr):
        line = data.partition("#")[0]
        try:
            return int(line)
        except ValueError:
            try:
                return float(line)
            except ValueError:
                print("ZON: could not parse number on line {}.".format(linenr))
                return None

    def from_int(self, value):
        return repr(int(value)).rstrip("L")

    def from_float(self, value):
        # Use general specifier with a very high precision.
        # Any spurious zeros are automatically removed. The precision
        # should be sufficient such that any numbers saved and loaded
        # back will have the exact same value again.
        # see e.g. http://bugs.python.org/issue1580
        return repr(float(value))  # '{:.17g}'.format(value)

    def from_unicode(self, value):
        value = value.replace("\\", "\\\\")
        value = value.replace("\n", "\\n")
        value = value.replace("\r", "\\r")
        value = value.replace("\x0b", "\\x0b").replace("\x0c", "\\x0c")
        value = value.replace("'", "\\'")
        return "'" + value + "'"

    def to_unicode(self, data, linenr):
        # Encode double slashes
        line = data.replace("\\\\", "0x07")  # temp

        # Find string using a regular expression
        m = re.search(r"'.*?[^\\]'|''", line)
        if not m:
            print("ZON: string not ended correctly on line {}.".format(linenr))
            return None  # return not-a-string
        else:
            line = m.group(0)[1:-1]

        # Decode stuff
        line = line.replace("\\n", "\n")
        line = line.replace("\\r", "\r")
        line = line.replace("\\x0b", "\x0b").replace("\\x0c", "\x0c")
        line = line.replace("\\'", "'")
        line = line.replace("0x07", "\\")
        return line

    def from_dict(self, value, indent):
        lines = ["dict:"]
        # Process children
        for key, val in value.items():
            # Skip all the builtin stuff
            if key.startswith("__"):
                continue
            # Skip methods, or anything else we can call
            if callable(val):
                continue
            # Add!
            lines.extend(self.from_object(key, val, indent + 2))
        return lines

    def to_dict(self, data, linenr):
        return Dict()

    def from_list(self, value, indent):
        # Collect subdata and check whether this is a "small list"
        isSmallList = True
        allowedTypes = (int, float, str)
        subItems = []
        for element in value:
            if not isinstance(element, allowedTypes):
                isSmallList = False
            subdata = self.from_object(None, element, 0)  # No indent
            subItems.extend(subdata)
        isSmallList = isSmallList and len(subItems) < 256

        # Return data
        if isSmallList:
            return "[{}]".format(", ".join(subItems))
        else:
            data = ["list:"]
            ind = " " * (indent + 2)
            for item in subItems:
                data.append(ind + item)
            return data

    def to_list(self, data, linenr):
        if data[0] == "l":  # list:
            return []
        else:
            i0 = 1
            pieces = []
            inString = False
            escapeThis = False
            line = data
            for i in range(1, len(line)):
                if inString:
                    # Detect how to get out
                    if escapeThis:
                        escapeThis = False
                        continue
                    elif line[i] == "\\":
                        escapeThis = True
                    elif line[i] == "'":
                        inString = False
                else:
                    # Detect going in a string, break, or end
                    if line[i] == "'":
                        inString = True
                    elif line[i] == ",":
                        pieces.append(line[i0:i])
                        i0 = i + 1
                    elif line[i] == "]":
                        piece = line[i0:i]
                        if piece.strip():  # Do not add if empty
                            pieces.append(piece)
                        break
            else:
                print("ZON: short list not closed right on line {}.".format(linenr))

            return [self.to_object(piece, linenr) for piece in pieces]
