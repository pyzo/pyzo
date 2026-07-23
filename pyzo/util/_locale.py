"""pyzo.util._locale
Module for locale stuff like language and translations.
"""

import os

import pyzo
from pyzo.qt import QtCore, QtWidgets

QLocale = QtCore.QLocale

# Define supported languages. The key defines the name as shown to the
# user. The value is passed to create a Locale object. From the local
# object we obtain the name for the .ts file.
L = QLocale.Language
LANGUAGES = {
    "English (US)": L.C,
    # == (L.English, L.UnitedStates),
    #'English (UK)': (L.English, L.UnitedKingdom),
    "Dutch": L.Dutch,
    "Spanish": L.Spanish,
    "Catalan": L.Catalan,
    "French": L.French,
    "German": L.German,
    "Italian": L.Italian,
    "Russian": L.Russian,
    "Polish": L.Polish,
    "Portuguese": L.Portuguese,
    "Portuguese (BR)": (L.Portuguese, QLocale.Country.Brazil),
    "Chinese (simplified)": L.Chinese,
    "Chinese (traditional)": (
        L.Chinese,
        QLocale.Country.Taiwan,
    ),  # https://bugreports.qt.io/browse/QTBUG-1573
    # Languages for which the is a .ts file, but no translations available yet:
    # "Slovak": L.Slovak,
}


LANGUAGE_SYNONYMS = {
    None: "English (US)",
    "": "English (US)",
    "English": "English (US)",
    "ca_ES": "Catalan",
    "de_DE": "German",
    "es_ES": "Spanish",
    "fr_FR": "French",
    "it_IT": "Italian",
    "nl_NL": "Dutch",
    "pl_PL": "Polish",
    "pt_BR": "Portuguese (BR)",
    "pt_PT": "Portuguese",
    "ru_RU": "Russian",
    "zh_CN": "Simplified Chinese",
    "zh_TW": "Traditional Chinese",
}


def getLocale(languageName):
    """Get the QLocale object for the given language (as a string)."""

    # Try System Language if nothing defined
    if languageName == "":
        languageName = QLocale.system().name()

    # Apply synonyms
    languageName = LANGUAGE_SYNONYMS.get(languageName, languageName)

    # if no language applicable, get back to default
    if LANGUAGES.get(languageName, None) is None:
        languageName = LANGUAGE_SYNONYMS.get("", "")

    # Select language in qt terms
    qtLanguage = LANGUAGES.get(languageName, None)
    if qtLanguage is None:
        raise ValueError("Unknown language")

    # Return locale
    if isinstance(qtLanguage, tuple):
        return QLocale(*qtLanguage)
    else:
        return QLocale(qtLanguage)


def setLanguage(languageName):
    """Set the language for the app. Loads qt and pyzo translations.

    Returns the QLocale instance to pass to the main widget.
    """

    # Get locale
    locale = getLocale(languageName)

    # Get paths were language files are
    qtTransPath = str(
        QtCore.QLibraryInfo.path(QtCore.QLibraryInfo.LibraryPath.TranslationsPath)
    )
    pyzoTransPath = os.path.join(pyzo.pyzoDir, "resources", "translations")

    # Get possible names for language files
    # (because Qt's .ts files may not have the country component.)
    localeName1 = locale.name()
    localeName2 = localeName1.split("_")[0]

    # Uninstall translators
    if not hasattr(QtCore, "_translators"):
        QtCore._translators = []
    for trans in QtCore._translators:
        QtWidgets.QApplication.removeTranslator(trans)

    # The default language
    if localeName1 == "C":
        return locale

    # Set Qt translations
    # Note that the translator instances must be stored
    # Note that the load() method is very forgiving with the file name
    for what, where in [("qt", qtTransPath), ("pyzo", pyzoTransPath)]:
        trans = QtCore.QTranslator()
        # Try loading both names
        for localeName in [localeName1, localeName2]:
            success = trans.load(what + "_" + localeName + ".qm", where)
            if success:
                QtWidgets.QApplication.installTranslator(trans)
                QtCore._translators.append(trans)
                print("loading {} {}: ok".format(what, languageName))
                break
        else:
            print("loading {} {}: failed".format(what, languageName))

    # Done
    return locale


class Translation(str):
    """Derives from str class. The translate function returns an instance
    of this class and assigns extra attributes:
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
    if ":::" in s:
        parts = s.split(":::", 1)
        return parts[0].rstrip(), parts[1].lstrip()
    else:
        return s, ""


def translate(context, text, disambiguation=None):
    """The translate function used throughout pyzo."""
    # Get translation and split tooltip
    newtext = QtCore.QCoreApplication.translate(context, text, disambiguation)
    s, tt = _splitMainAndTt(newtext)
    # Create translation object (string with extra attributes)
    translation = Translation(s)
    translation.original = text
    translation.tt = tt
    translation.key = _splitMainAndTt(text)[0].strip()
    return translation


if __name__ == "__main__":
    # Print names of translator files

    print("Language data files:")
    for key in LANGUAGES:
        s = "{}: {}".format(key, getLocale(key).name() + ".ts")
        print(s)
