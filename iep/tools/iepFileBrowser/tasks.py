# -*- coding: utf-8 -*-
# Copyright (C) 2012 Almar Klein

""" 
Define tasks that can be executed by the file browser.
These inherit from proxies.Task and implement that specific interface.
"""

import re
from . import proxies


class SearchTask(proxies.Task):
    __slots__ = []
    
    def process(self, proxy, param):
        return self._process(proxy, **param)
    
    def _process(self, proxy, pattern=None, matchCase=False, regExp=False, **rest):
        
        # Quick test
        if not pattern:
            return
        
        # Get text
        text = self._getText(proxy)
        if not text:
            return
        
        # Get search text. Deal with case sensitivity
        searchText = text
        if not matchCase:
            searchText = searchText.lower()
            pattern = pattern.lower()
        
        # Search indices
        if regExp:
            indices = self._getIndicesRegExp(searchText, pattern)
        else:
            indices = self._getIndicesNormal1(searchText, pattern)
        
        # Return as lines
        if indices:
            return self._indicesToLines(text, indices)
        else:
            return []
    
    
    def _getText(self, proxy):
        
        # Init
        path = proxy.path()
        fsProxy = proxy._fsProxy
       
        # Get file size
        try:
            size = fsProxy.fileSize(path)
        except NotImplementedError:
            pass
        size = size or 0
        
        # Search all Python files. Other files need be < xx bytes
        if path.lower().endswith('.py') or size < 100*1024:
            pass
        else:
            return None 
        
        # Get text
        bb = fsProxy.read(path)
        if bb is None:
            return
        try:
            return bb.decode('utf-8')
        except UnicodeDecodeError:
            # todo: right now we only do Unicode
            return None
    
    
    def _getIndicesRegExp(self, text, pattern):
        indices = []
        for match in re.finditer(pattern, text, re.MULTILINE | re.UNICODE):
                indices.append( match.start() )
        return indices
    
    
    def _getIndicesNormal1(self, text, pattern):
        indices = []
        i = 0
        while i>=0:
            i = text.find(pattern,i+1)
            if i>=0:
                indices.append(i)
        return indices
    
    
    def _getIndicesNormal2(self, text, pattern):
        indices = []
        i = 0
        for line in text.splitlines(True):
            i2 = line.find(pattern)
            if i2>=0:
                indices.append(i+i2)
            i += len(line)
        return indices
    
    
    def _indicesToLines(self, text, indices):
        
        # Determine line endings
        LE = self._determineLineEnding(text)
        
        # Obtain line and line numbers
        lines = []
        for i in indices:
            # Get linenr and index of the line
            linenr = text.count(LE, 0, i) + 1                
            i1 = text.rfind(LE, 0, i)
            i2 = text.find(LE, i)
            # Get line and strip
            if i1<0:
                i1 = 0
            line = text[i1:i2].strip()[:80]
            # Store
            lines.append( (linenr, repr(line)) )
        
        # Set result
        return lines
    
    
    def _determineLineEnding(self, text):
        """ function to determine quickly whether LF or CR is used
        as line endings. Windows endings (CRLF) result in LF
        (you can split lines with either char).
        """
        i = 0
        LE = '\n'
        while i < len(text):
            i += 128
            LF = text.count('\n', 0, i)
            CR = text.count('\r', 0, i)
            if LF or CR:
                if CR > LF:
                    LE = '\r'
                break
        return LE



class DocstringTask(proxies.Task):
    __slots__ = []
    
    def process(self, proxy, param):
        path = proxy.path()
        fsProxy = proxy._fsProxy
        
        # Search only Python files
        if not path.lower().endswith('.py'):
            return None
        
        # Get text
        bb = fsProxy.read(path)
        if bb is None:
            return
        try:
            text = bb.decode('utf-8')
            del bb
        except UnicodeDecodeError:
            # todo: right now we only do Unicode
            return
        
        # Find docstring
        lines = []
        delim = None # Not started, in progress, done        
        count = 0
        for line in text.splitlines():
            count += 1
            if count > 200:
                break
            if delim and '"""' in line or "'''" in line:
                break
            elif line.startswith('"""'):
                delim = '"""'
                line = line.lstrip('"')
            elif line.startswith("'''"):
                delim = "'''"
                line = line.lstrip("'")
            if delim:
                lines.append(line)
        
        # Limit number of lines
        if len(lines) > 5:
            lines = lines[:5] + ['...']
        # Make text and strip
        doc = '\n'.join(lines)
        doc = doc.strip()
        if len(doc) > 250:
            doc = doc[:247] + '...'
        
        # Fill in if no docstring detected in X lines
        if not doc:
            doc = 'No docstring detected'
        
        return doc
