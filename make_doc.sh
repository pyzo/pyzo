#!/bin/bash

cd doc
sphinx-build -D html_theme=agogo -b qthelp -d _build/doctrees . _build/qthelp
cd ..
qhelpgenerator-qt4 doc/_build/qthelp/IEP.qhp -o iep/resources/iep.qch

