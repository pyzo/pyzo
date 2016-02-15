# -*- coding: utf-8 -*-
# Copyright (C) 2013, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" Code related to the license.
"""

import os
import sys
import datetime

import iep
from pyzolib.qt import QtCore, QtGui


LICENSEKEY_FILE = os.path.join(iep.appDataDir, "licensekey.txt")

UNMANGLE_CODE ="""
eJytU8Fu2zAMvecr2OQgGXOMJU23wVgOOfQwdLcAK4piGFSJToS5UiDJ6Yph/z5KVpxm7YYe5ost
8r1HPoqewDW2LShr8AxubAf3wogNKggWFEqrEMIWodUSjUfoDOU3LULTGRm0NWejCUzB4UY45UtY
S41GIqx2u1ajGilsBg73RT0CesbjMXzuBaff8TGW8sFps0lFtQzVAZbeO4eN/lHCtxL8Apbgq4je
8aLaCRd07IKzKSuegAl1Jzy+W1S9h7vHgJ73uYoapBBnwkutWVFkDGddaKYfso5uwNgAmQPCKCqe
+4+PE5rG8UW0HV46Zx1nV+QkUrSB9Qoa6+5FqE7VcgM+UN/+QYctZ+vV1eUN+z/CsFxCL7ifsX8p
fjJ70WoFe3Sepge2ea7sz18eol+8boB+TnzG0re0nQl0fJ9OVAdkdOPPj032kDcHTPJGDOsUlwVt
WMoPqYetph3UH98eBXoGCcwvLoYgNUERuXVc565mf3E1f50rRfSfvwYbcQGTk1nlaeEDZ3VdP73N
BFimV95aVmepfH10jgoRcWKGfowS6JoGdtZn5ezIx9bj6Qj+oJWHK8jVKH2KV7cU+kpo4vQObxlF
WAx5gAkIpSIr5RyGzhlQvwFvTS4N
"""


import types, base64, zlib
def parse_license(key):
    """ Unmangle the license key and return a dict with license info.
    The dict at least has these fields: 
    name, company, email, expires, product, reference.
    
    The actual code of this function is obfuscated. We realize that
    anyone with a bit of free time can find out the license parsing.
    The obfuscating is to make this a bit harder and to avoid having
    the code verbatim in the repository.
    
    You are free to reverse-engineer our license key format and then
    produce your own license. However, who would you be fooling?
    """
    # Define function
    codeb = zlib.decompress(base64.decodebytes(UNMANGLE_CODE.encode('ascii')))
    exec(codeb.decode('utf-8'), globals())
    # Call it
    return unmangle(key)
    



def get_keys():
    """ Get a list of all license keys, in the order that thet were added.
    """
    
    # Get text of license file
    if os.path.isfile(LICENSEKEY_FILE):
        text = open(LICENSEKEY_FILE, 'rt').read()
    else:
        text = ''
    
    # Remove comments
    lines = []
    for line in text.splitlines():
        if line.startswith('#'):
            line = ''
        lines.append(line.rstrip())
    
    # Split in licenses
    licenses = ('\n'.join(lines)).split('\n\n')
    licenses = [key.strip() for key in licenses]    
    licenses = [key for key in licenses if key]
    
    # Remove duplicates (avoid set() to maintain order)
    licenses, licenses2 = [], licenses
    for key in licenses2:
        if key not in licenses:
            licenses.append(key)
    
    # Sort and return    
    return licenses


def is_invalid(info):
    """ Get whether a license is invalid. Returns a string with the reason.
    """
    # IEP license?
    if not ('IEP' in info['product'].upper() or 
            'PYZO' in info['product'].upper() ):
        return 'This is not an IEP license.'
    # Expired
    today = datetime.datetime.now().strftime('%Y%m%d')
    if today > info['expires']:
        return 'The license has expired'


def get_license_info():
    """ Get the license info of the most recently added valid license.
    Returns a dict which at least has these fields: 
    name, company, email, expires, product, reference.
    Returns None if there is no valid license.
    """
    
    # Get all keys
    keys = get_keys()
    
    # Get valid licenses
    valid_licenses = []
    for key in keys:
        info = parse_license(key)
        if not is_invalid(info):
            valid_licenses.append(info)
    
    # Done
    if valid_licenses:
        return valid_licenses[-1]
    else:
        return None



def add_license(key):
    """ Add a license key to IEP.
    """
    
    # Normalize and check license
    key = key.strip().replace('\n', '').replace('\r', '')
    info = parse_license(key)
    invalid = is_invalid(info)
    if invalid:
        raise ValueError('Given license is not valid: %s' % invalid)
    
    # Get licenses and add our key
    licenses = get_keys()
    licenses.append(key)
    
    # Remove duplicates (avoid set() to maintain order)
    licenses, licenses2 = [], licenses
    for key in licenses2:
        if key not in licenses:
            licenses.append(key)
    
    # Write back
    lines = ['# List of license keys for IEP', '']
    for key in licenses:
        info = parse_license(key)
        comment = '# Licensed to {name} expires {expires}'.format(**info)
        lines.append(comment)
        lines.append(key)
        lines.append('')
    with open(LICENSEKEY_FILE, 'wt') as f:
        f.write('\n'.join(lines))



class LicenseManager(QtGui.QDialog):
    """ Dialog to view current licenses and to add license keys.
    """
    
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle(iep.translate("menu dialog", "Manage IEP license keys"))
        self.resize(500,500)
        
        # Create button to add license key
        self._addbut = QtGui.QPushButton(
            iep.translate("menu dialog", "Add license key") )
        self._addbut.clicked.connect(self.addLicenseKey)
        
        # Create label with link to website
        self._linkLabel = QtGui.QLabel(self)
        self._linkLabel.setTextFormat(QtCore.Qt.RichText)
        self._linkLabel.setOpenExternalLinks(True)
        self._linkLabel.setText("You can purchase a license at " + 
            "<a href='http://iep-project.org/contributing.html'>http://iep-project.org</a>")
        self._linkLabel.setVisible(False)
        
        # Create label to show license info
        self._label = QtGui.QTextEdit(self)
        self._label.setLineWrapMode(self._label.WidgetWidth)
        self._label.setReadOnly(True)
         
        # Layout
        layout = QtGui.QVBoxLayout(self)
        self.setLayout(layout)
        layout.addWidget(self._addbut)
        layout.addWidget(self._linkLabel)
        layout.addWidget(self._label)
        
        # Init
        self.showLicenses()
    
    
    def addLicenseKey(self):
        """ Show dialog to insert new key.
        """
        # Ask for key
        title = iep.translate("menu dialog", "Add license key")
        label = ''
        s = PlainTextInputDialog.getText(self, title, label)
        if isinstance(s, tuple):
            s = s[0] if s[1] else ''
        
        # Add it
        if s:
            try:
                add_license(s)
            except Exception as err:
                label = 'Could not add label:\n%s' % str(err)
                QtGui.QMessageBox.warning(self, title, label)
        
        # Update
        self.showLicenses()
        iep.license = get_license_info()
    
    
    def showLicenses(self):
        """ Show all licenses.
        """
        # Get active license
        activeLicense = get_license_info()
        
        # Get all keys, transform to license dicts
        license_keys = get_keys()
        license_dicts = [parse_license(key) for key in license_keys]
        license_dicts.sort(key=lambda x:x['expires'])
        
        lines = ['<p>Listing licenses from <i>%s</i></p>' % LICENSEKEY_FILE]
        for info in reversed(license_dicts):
            # Get info             
            activeText = ''
            key = info['key']
            if activeLicense and activeLicense['key'] == key:
                activeText = ' (active)'
            e = datetime.datetime.strptime(info['expires'], '%Y%m%d')
            expires = e.strftime('%d-%m-%Y')
            # Create summary
            lines.append('<p>')
            lines.append('<b>%s</b>%s<br />' % (info['product'], activeText))
            lines.append('Name: %s<br />' % info['name'])
            lines.append('Email: %s<br />' % info['email'])
            lines.append('Company: %s<br />' % info['company'])
            lines.append('Expires: %s<br />' % expires)
            lines.append('key: <tiny><sub>%s</sub></tiny><br />' % key)
            lines.append('</p>')
        
        # No licenses?
        if not license_dicts:
            lines.insert(1, '<p>No license keys found.</p>')
            self._linkLabel.setVisible(True)
        elif not activeLicense:
            lines.insert(1, '<p>All your keys seem to have expired.</p>')
            self._linkLabel.setVisible(True)
        else:
            self._linkLabel.setVisible(False)
        
        # Set label text
        self._label.setHtml('\n'.join(lines))


class PlainTextInputDialog(QtGui.QDialog):
    def __init__(self, parent, title='', label=''):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle(title)
        
        self._result = None  # Default (when closed with cross)
        
        # Layout
        gridLayout = QtGui.QGridLayout(self)
        self.setLayout(gridLayout)
        
        # Create label
        self._label = QtGui.QLabel(label, self)
        gridLayout.addWidget(self._label, 0,0,1,1)
        
        # Create text edit
        self._txtEdit = QtGui.QPlainTextEdit(self)
        gridLayout.addWidget(self._txtEdit, 1,0,1,1)
        
        # Create button box
        self._butBox = QtGui.QDialogButtonBox(self)
        self._butBox.setOrientation(QtCore.Qt.Horizontal)
        self._butBox.setStandardButtons(self._butBox.Cancel | self._butBox.Ok)
        gridLayout.addWidget(self._butBox, 2,0,1,1)
        
        # Signals
        self._butBox.accepted.connect(self.on_accept)
        self._butBox.rejected.connect(self.on_reject)
    
    def on_accept(self):
        self.setResult(1)
        self._result = self._txtEdit.toPlainText()
        self.close()
    
    def on_reject(self):
        self.setResult(0)
        self._result = None
        self.close()
    
    @classmethod
    def getText(cls, parent, title='', label=''):
        d = PlainTextInputDialog(parent, title, label)
        d.exec_()
        return d._result

    
if __name__ == '__main__':
    w = LicenseManager(None)
    w.show()
    #print(PlainTextInputDialog.getText(None, 'foo', 'bar'))
    

    
