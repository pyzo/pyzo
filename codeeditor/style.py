""" Modyule style

Provides basic functionaliy for styling.

"""

class StyleFormat:
    """ StyleFormat(format='')
    
    Represents the style format for a specific style element.
    A "style" is a dictionary that maps names to StyleFormat instances.
    
    The given format can be a string or another StyleFormat instance.
    Style formats can be combined using their update() method. 
    
    A style format consists of multiple parts, where each "part" consists
    of a key and a value. The keys can be basically anything, depending
    on what kind of thing is being styled. Some example keys are:
      * fore: the foreground color
      * back: the background color
      * bold: whether the text should be bold
      * underline: whether an underline should be used (and which one)
      * italic: whether the text should be in italic
    
    The format neglects spaces and case. Parts are separated by commas 
    or semicolons. If only a key is given it's value is interpreted
    as 'yes'. If only a color is given, its key is interpreted as 'fore'.
    
    An example format string: 'fore:#334, bold, underline:dotLine'
    
    By calling str(styleFormatInstance) the string representing the 
    format can be obtained. By iterating over the instance, a series 
    of key-value pairs is obtained.
    
    """
    
    def __init__(self, format=''):
        self._parts = {}
        self.update(format)
    
    
    def __str__(self):
        """ Get a (cleaned up) string representation of this style format. 
        """
        parts = []
        for key in self._parts:
            parts.append('%s:%s' % (key, self._parts[key]))
        return ', '.join(parts)
    
    
    def __repr__(self):
        return '<StyleFormat "%s">' % str(self)
    
    
    def __iter__(self):
        """ Yields a series of tuples (key, val).
        """
        parts = []
        for key in self._parts:
            parts.append( (key, self._parts[key]) )
        return parts.__iter__()
    
    
    def update(self, format):
        """ update(format)
        
        Update this style format with the given format.
        
        """
        
        # Make a string, so we update the format with the given one
        if isinstance(format, StyleFormat):
            format = str(format)
        
        # Split on ',' and ':', ignore spaces
        styleParts = [p for p in format.replace(';',',').split(',')]
        
        for stylePart in styleParts:
            
            # Make sure it consists of identifier and value pair
            # e.g. fore:#xxx, bold:yes, underline:no
            if not ':' in stylePart:
                if stylePart.startswith('#'):
                    stylePart = 'fore:' + stylePart
                else:
                    stylePart += ':yes'
            
            # Get key value and strip and make lowecase
            key, _, val = [i.strip().lower() for i in stylePart.partition(':')]
            
            # Store in parts
            if key:
                self._parts[key] = val


# todo: include category, or maybe name with dots?
class StyleElementDescription:
    """ StyleElementDescription(name, defaultFormat, description)
    
    Describes a style element by its name, description and default format.
    
    A style description is a simple placeholder for something
    that can be styled.
    """
    
    def __init__(self, name, defaultFormat, description):
        self._name = name
        self._defaultFormat = defaultFormat
        self._description = description
    
    @property
    def name(self):
        return self._name
    
    @property
    def key(self):
        return self._name.replace(' ', '').lower()
    
    @property
    def description(self):
        return self._description
    
    @property
    def defaultFormat(self):
        return self._defaultFormat
