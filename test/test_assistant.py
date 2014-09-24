
"""
    Test cases for the assistant component.
    Depends on:
    - pytest
    - pytest-qt

    Run:
    $ py.test test/
    or 
    $ python -m pytest test/
"""

import os

from iep.iepcore.assistant import IepAssistant


my_dir = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))
test_doc_file = os.path.join(my_dir, 'pySerial.qch')


def test_add_doc(qtbot, tmpdir):
    # Setup empty collection file:
    col_file = str(tmpdir.join('test_col.qhc'))
    assistant = IepAssistant(collection_filename=col_file)
    assistant.show()
    qtbot.addWidget(assistant)
    assert [] == assistant._engine.registeredDocumentations()

    assistant._settings.add_doc_do(test_doc_file)
    assert 1 == len(assistant._engine.registeredDocumentations())


def test_add_del_doc(qtbot, tmpdir):
    col_file = str(tmpdir.join('test_col.qhc'))
    assistant = IepAssistant(collection_filename=col_file)
    qtbot.addWidget(assistant)
    assert [] == assistant._engine.registeredDocumentations()

    assistant._settings.add_doc_do(test_doc_file)
    assert 1 == len(assistant._engine.registeredDocumentations())

    # Get registered documentation:
    reg_doc = assistant._engine.registeredDocumentations()[0]
    assistant._settings.del_doc_do(reg_doc)
    assert 0 == len(assistant._engine.registeredDocumentations())
