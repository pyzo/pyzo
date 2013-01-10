# -*- coding: utf-8 -*-
# Copyright (C) 2012, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" iep.util.locale
Module for locale stuff like language and translations.
"""

import os, sys
from iep.codeeditor.qt import QtCore, QtGui

import iep


# Define supported languages. The key defines the name as shown to the
# user. The value is passed to create a Locale object. From the local
# object we obtain the name for the .tr file.
LANGUAGES = {
    'English (US)': QtCore.QLocale.C, 
    # == (QtCore.QLocale.English, QtCore.QLocale.UnitedStates),
    #'English (UK)': (QtCore.QLocale.English, QtCore.QLocale.UnitedKingdom),
    'Dutch': QtCore.QLocale.Dutch,
    }


LANGUAGE_SYNONYMS = {   None: 'English (US)',
                        '': 'English (US)',
                        'English': 'English (US)'}


def getLocale(languageName):
    """ getLocale(languageName)
    Get the QtCore.QLocale object for the given language (as a string).
    """
    
    # Apply synonyms
    languageName = LANGUAGE_SYNONYMS.get(languageName, languageName)
    
    # Select language in qt terms
    qtLanguage = LANGUAGES.get(languageName, None)
    if qtLanguage is None:
        raise ValueError('Unknown language')
    
    # Return locale
    if isinstance(qtLanguage, tuple):
        return QtCore.QLocale(*qtLanguage)
    else:
        return QtCore.QLocale(qtLanguage)


def setLanguage(languageName):
    """ setLanguage(languageName)
    Set the language for the app. Loads qt and iep translations.
    Returns the QLocale instance to pass to the main widget.
    """
    
    # Get locale
    locale = getLocale(languageName)
    
    # Get paths were language files are
    qtTransPath = str(QtCore.QLibraryInfo.location(
                    QtCore.QLibraryInfo.TranslationsPath))
    iepTransPath = os.path.join(iep.iepDir, 'resources')
    
    # Get possible names for language files
    localeName1 = locale.name()
    localeName2 = localeName1.split('_')[0]
    
    # The default language 
    # todo: must we not uninstall any existing translators?
    if localeName1 == 'C':
        return locale
    
    # Set Qt translations
    # Note that the translator instances must be stored
    # Note that the load() method is very forgiving with the file name
    QtCore._translators = []
    for what, where in [('qt', qtTransPath),('iep', iepTransPath)]:
        trans = QtCore.QTranslator()
        
        # Try loading both names
        for localeName in [localeName1, localeName2]:
            success = trans.load(what + '_' + localeName + '.tr', where)
            if success:
                QtGui.QApplication.installTranslator(trans)
                QtCore._translators.append(trans)
                print('loading %s %s: ok' % (what, languageName))
                break
        else:
            print('loading %s %s: failed' % (what, languageName))
    
    # Done
    return locale



class Translation(str):
    """ Derives from str class. The translate function returns an instance
    of this class and assigns extra atrributes:
      * original: the original text passed to the translation
      * tt: the tooltip text 
      * key: the original text without tooltip (used by menus as a key)
    
    We adopt a simple system to include tooltip text in the same
    translation as the label text. By including ":::" in the text,
    the text after that identifier is considered the tooltip.
    The text returned by the translate function is always the 
    string without tooltip, but the text object has an attribute
    "tt" that stores the tooltip text. In this way, if you do not
    use this feature or do not know about this feature, everything
    keeps working as expected.
    """
    pass


def _splitMainAndTt(s):
        if ':::' in s:
            parts = s.split(':::', 1)
            return parts[0].rstrip(), parts[1].lstrip()
        else:
            return s, ''


def translate(context, text, disambiguation=None):  
    """ translate(context, text, disambiguation=None)
    The translate function used throughout IEP.
    """
    # Get translation and split tooltip
    newtext = QtCore.QCoreApplication.translate(context, text, disambiguation)
    s, tt = _splitMainAndTt(newtext)
    # Create translation object (string with extra attributes)
    translation = Translation(s)
    translation.original = text
    translation.tt = tt
    translation.key = _splitMainAndTt(text)[0].strip()
    return translation


if __name__ == '__main__':
    # Print names of translator files
    
    print('Language data files:')
    for key in LANGUAGES:
        s = '{}: {}'.format(key, getLocale(key).name()+'.tr')
        print(s)
