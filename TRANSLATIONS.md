Many texts in Pyzo are translatable to other languages. Currently, we
have translations for Dutch, German, French, Spanish, Catalan, Polish,
Portuguese, Brazilian Portuguese, Russian, Traditional Chinese,
Simplified Chinese, Italian.

For the translations we make use of Qt's translation system. To update
a translation, run Qt linguist on any of the `.ts` files
[here](https://github.com/pyzo/pyzo/tree/main/pyzo/resources/translations).
One way to obtain the "Qt Linguist" tool is via `pip install pyside6`.
Then you will have an executable "pyside6-linguist" in the same folder
as your Python executable.
Finally, submit the result, preferably via a GitHub pull request.

The translation texts contain triple colons to separate the regular
text from a more detailed text that will be shown in the tooltip, e.g.
"open ::: open a new file".

If you want to add translations for a new language, open a discussion
or create an issue on [Pyzo's GitHub page](https://github.com/pyzo/pyzo).
We will then create and give you the appropriate `.ts` file.

There are also many text that are not yet translatable, you can also
help by modifying the code such that these strings are passed through
the `translate()` function.

If you have no GitHub account, it is also fine to contact the Pyzo developers
via email.

For developers:
Use the script "pyzo/resources/translations/translations_helper.py" for
creating and updating translations. Detailed instructions are inside that
script.
