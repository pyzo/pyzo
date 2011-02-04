
class StyleFormat:
    """
    Names:
      * style: a dict mapping name -> style element
      * style element -> a representation of a style e.g. 'fore:#050, bold' 
      * style element part -> the parts in such an element
    
    """
    def __init__(self, element=''):
        self._parts = {}
        self.update(element)
    
    
    def __str__(self):
        """ Get a (cleaned up) string representation of this style element. 
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
    
    
    def update(self, element):
        
        # Make a string, so we update the element with the given one
        if isinstance(element, StyleFormat):
            element = str(element)
        
        # Split on ',' and ':', ignore spaces
        styleParts = [p for p in element.replace(';',',').split(',')]
        
        for stylePart in styleParts:
            
            # Make sure it consists of identifier and value pair
            # e.g. fore:#xxx, bold:yes, underline:no
            if not ':' in stylePart:
                if stylePart.startswith('#'):
                    stylePart = 'fore:' + stylePart
                else:
                    stylePart += ':yes'
            
            # Get key value and strip and make lowecase
            tmp = [i.strip().lower() for i in stylePart.split(':')]
            key = tmp[0]
            val = tmp[1]
            
            # Store in parts
            if key:
                self._parts[key] = val


class StyleDescription:
    """ Base style description class. 
    A style description is a simple placeholder for something
    that can be styled.
    """

class CurrentLineDescription(StyleDescription):
    """ Describes the backgound color of the current line. """
    defaultStyle = '#f5f'

class LineNumberDescription(StyleDescription):
    """ Describes the color and background color of the line numbers. """
    defaultStyle = 'fore:#444, back:#aaa'
