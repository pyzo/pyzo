#!/bin/bash

cd doc
make qthelp
cd ..
qhelpgenerator-qt4 doc/_build/qthelp/IEP.qhp -o iep/resources/iep.qch

