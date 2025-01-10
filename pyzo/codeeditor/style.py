"""Module style

Provides basic functionality for styling.

Styling is done using a dictionary of StyleFormat instances. Each
such instance represents a certain element being styled (e.g. keywords,
line numbers, indentation guides).

All possible style elements are represented using StyleElementDescription
instances. These have a name, description and default format, which
makes it easy to build a UI to allow the user to change the style.

"""

from .qt import QtGui, QtCore

Qt = QtCore.Qt


class StyleElementDescription:
    """StyleElementDescription(name, defaultFormat, description)

    Describes a style element by its name, default format, and description.

    A style description is a simple placeholder for something
    that can be styled.

    """

    def __init__(self, name, description, defaultFormat):
        self._name = name
        self._description = description
        self._defaultFormat = StyleFormat(defaultFormat)

    def __repr__(self):
        return '<"{}": "{}">'.format(self.name, self.defaultFormat)

    @property
    def name(self):
        return self._name

    @property
    def key(self):
        return self._name.replace(" ", "").lower()

    @property
    def description(self):
        return self._description

    @property
    def defaultFormat(self):
        return self._defaultFormat


class StyleFormat:
    """StyleFormat(format='')

    Represents the style format for a specific style element.
    A "style" is a dictionary that maps names (of style elements)
    to StyleFormat instances.

    The given format can be a string or another StyleFormat instance.
    Style formats can be combined using their update() method.

    A style format consists of multiple parts, where each "part" consists
    of a key and a value. The keys can be anything, depending
    on what kind of thing is being styled. The value can be obtained using
    the index operator (e.g. styleFomat['fore'])

    For a few special keys, properties are defined that return the Qt object
    corresponding to the value. These values are also buffered to enable
    fast access. These keys are:
      * fore: (QColor) the foreground color
      * back: (QColor) the background color
      * bold: (bool) whether the text should be bold
      * italic: (bool) whether the text should be in italic
      * underline: (int) whether an underline should be used (and which one)
      * linestyle: (int) what line style to use (e.g. for indent guides)
      * textCharFormat: (QTextCharFormat) for the syntax styles

    The format neglects spaces and case. Parts are separated by commas
    or semicolons. If only a key is given it's value is interpreted
    as 'yes'. If only a color is given, its key is interpreted as 'fore'
    and back. Colors should be given using the '#' hex formatting.

    An example format string: 'fore:#334, bold, underline:dotLine'

    By calling str(styleFormatInstance) the string representing of the
    format can be obtained. By iterating over the instance, a series
    of key-value pairs is obtained.

    """

    def __init__(self, format=""):
        self._parts = {}
        self.update(format)

    def _resetProperties(self):
        self._fore = None
        self._back = None
        self._bold = None
        self._italic = None
        self._underline = None
        self._linestyle = None
        self._textCharFormat = None

    def __str__(self):
        """Get a (cleaned up) string representation of this style format."""
        parts = ["{}:{}".format(key, self._parts[key]) for key in self._parts]
        return ", ".join(parts)

    def __repr__(self):
        return '<StyleFormat "{}">'.format(self)

    def __getitem__(self, key):
        try:
            return self._parts[key]
        except KeyError:
            raise KeyError("Invalid part key " + key + " for style format.")

    def __iter__(self):
        """Yields a series of tuples (key, val)."""
        parts = [(key, self._parts[key]) for key in self._parts]
        return parts.__iter__()

    def update(self, format):
        """Update this style format with the given format."""

        # Reset buffered values
        self._resetProperties()

        # Make a string, so we update the format with the given one
        if isinstance(format, StyleFormat):
            format = str(format)

        # Split on ',' and ','
        styleParts = format.replace("=", ":").replace(";", ",").split(",")

        for stylePart in styleParts:
            # Make sure it consists of identifier and value pair
            # e.g. fore:#xxx, bold:yes, underline:no
            if ":" not in stylePart:
                if stylePart.startswith("#"):
                    stylePart = "foreandback:" + stylePart
                else:
                    stylePart += ":yes"

            # Get key value and strip and make lowecase
            key, _, val = [i.strip().lower() for i in stylePart.partition(":")]

            # Store in parts
            if key == "foreandback":
                self._parts["fore"] = val
                self._parts["back"] = val
            elif key:
                self._parts[key] = val

    ## Properties

    def _getValueSafe(self, key):
        try:
            return self._parts[key]
        except KeyError:
            return "no"

    @property
    def fore(self):
        if self._fore is None:
            self._fore = QtGui.QColor(self._parts["fore"])
        return self._fore

    @property
    def back(self):
        if self._back is None:
            self._back = QtGui.QColor(self._parts["back"])
        return self._back

    @property
    def bold(self):
        if self._bold is None:
            self._bold = self._getValueSafe("bold") in ["yes", "true"]
        return self._bold

    @property
    def italic(self):
        if self._italic is None:
            self._italic = self._getValueSafe("italic") in ["yes", "true"]
        return self._italic

    @property
    def underline(self):
        if self._underline is None:
            US = QtGui.QTextCharFormat.UnderlineStyle
            val = self._getValueSafe("underline")
            if val in ["yes", "true"]:
                self._underline = US.SingleUnderline
            elif val in ["dotted", "dots", "dotline"]:
                self._underline = US.DotLine
            elif val in ["wave"]:
                self._underline = US.WaveUnderline
            else:
                self._underline = US.NoUnderline
        return self._underline

    @property
    def linestyle(self):
        if self._linestyle is None:
            val = self._getValueSafe("linestyle")
            if val in ["yes", "true"]:
                self._linestyle = Qt.PenStyle.SolidLine
            elif val in ["dotted", "dot", "dots", "dotline"]:
                self._linestyle = Qt.PenStyle.DotLine
            elif val in ["dashed", "dash", "dashes", "dashline"]:
                self._linestyle = Qt.PenStyle.DashLine
            else:
                self._linestyle = Qt.PenStyle.SolidLine  # default to solid
        return self._linestyle

    @property
    def textCharFormat(self):
        if self._textCharFormat is None:
            self._textCharFormat = QtGui.QTextCharFormat()
            self._textCharFormat.setForeground(self.fore)
            try:  # not all styles have a back property
                self._textCharFormat.setBackground(self.back)
            except Exception:
                pass
            self._textCharFormat.setUnderlineStyle(self.underline)
            if self.bold:
                self._textCharFormat.setFontWeight(QtGui.QFont.Weight.Bold)
            if self.italic:
                self._textCharFormat.setFontItalic(True)
        return self._textCharFormat
