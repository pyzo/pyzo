Many texts in Pyzo are translatable to other languages. Currently, we
have translations for Dutch, German, French, Spanish, Catalan,
Portuguese, Brazilian Portuguese, Russian, Traditional Chinese,
Simplified Chinese.

For the translations we make use of Qt's translation system. To update
a translation, run Qt linguist on any of the `.tr` files
[here](https://github.com/pyzo/pyzo/tree/master/pyzo/resources/translations).
Then submit the result, preferably via a Github pull request (but
emailing it to me is fine too).

The translation texts contain double colons to separate the regular
text from a more detailed text that will be shown in the tooltip, e.g.
"open :: open a new file".

If you want to add translations for a new language, send me an email
or make an issue so that I can create the appropriate `.tr` file.

There are also many text that are not yet translatable, you can also
help by modifying the code such that these strings are passed through
the `translate()` function.
