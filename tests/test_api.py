import sys
import pyzo
import subprocess


def test_api():
    assert pyzo.__version__


qt_libs = ["PySide2", "PySide6", "PyQt5", "PyQt6"]

code1 = """
import sys
import pyzo
print(list(sys.modules.keys()))
"""


def test_import1():
    x = subprocess.check_output([sys.executable, "-c", code1])
    modules = eval(x.decode())
    assert isinstance(modules, list)
    assert "sys" in modules
    assert "pyzo" in modules

    assert "pyzo.core" not in modules
    assert not any(qt_lib in modules for qt_lib in qt_libs)

    assert "pyzo.qt" not in modules


code2 = """
import sys
import pyzo
import pyzo.qt
print(list(sys.modules.keys()))
"""


def test_import2():
    x = subprocess.check_output([sys.executable, "-c", code2])
    modules = eval(x.decode())
    assert isinstance(modules, list)
    assert "sys" in modules
    assert "pyzo" in modules

    assert "pyzo.qt" in modules
    assert any(qt_lib in modules for qt_lib in qt_libs)

    assert "pyzo.core" not in modules


test_import1()
test_import2()
