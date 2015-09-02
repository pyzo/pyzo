import os
import sys
import time
import struct
import shutil
import threading
import subprocess
import urllib.request

from pyzolib.qt import QtCore, QtGui

from pyzolib import paths

miniconda = 'Miniconda3-latest-Windows-x86_64.exe'
miniconda = r'C:\Users\almar\Downloads' + '\\' + miniconda

def download_miniconda(path):
    pass


def is_64bit():
    """ Get whether the OS is 64 bit.
    """
    if sys.platform.startswith('win'):
        if 'PROCESSOR_ARCHITEW6432' in os.environ:
            return True
        return os.environ['PROCESSOR_ARCHITECTURE'].endswith('64')
    else:
        return struct.calcsize('P') == 8


def py_exe(dir):
    if sys.platform.startswith('win'):
        return os.path.join(dir, 'python.exe')
    else:
        return os.path.join(dir, 'bin', 'python')


def check_our_conda():
    
    conda_dir = os.path.join(paths.appdata_dir('iep'), 'conda_root')
    
    # # Do we already have a conda env?
    # if os.path.isfile(py_exe(conda_dir)):
    #     # todo: no remove, but return
    #     shutil.rmtree(conda_dir)
    #     #return  # no action required
    
    # todo: did the user previously specify he did not want a conda env?
    
    # Does he want a conda env now?
    d = AskToInstallConda()
    d.exec_()
    if not d.result():
        return
    
    # Launch installer
    d = Installer(conda_dir)
    d.exec_()

class AskToInstallConda(QtGui.QDialog):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setModal(True)
        
        text = 'To program in Python, you need a Python environment.\n\n'
        text += 'Do you want IEP to install a Python environment (via Conda)?\n'
        text += 'If not, you must arrange for a Python interpreter yourself'
        if not sys.platform.startswith('win'):
            text += ' or use the system Python.'
        text += '.'
        
        self._label = QtGui.QLabel(text, self)
        self._no = QtGui.QPushButton("No thanks")
        self._yes = QtGui.QPushButton("Yes, please install Python!")
        
        self._no.clicked.connect(self.reject)
        self._yes.clicked.connect(self.accept)
        
        vbox = QtGui.QVBoxLayout(self)
        hbox = QtGui.QHBoxLayout()
        self.setLayout(vbox)
        vbox.addWidget(self._label, 1)
        vbox.addLayout(hbox, 0)
        hbox.addWidget(self._no, 2)
        hbox.addWidget(self._yes, 2)
        
        self._yes.setDefault(1)


class Installer(QtGui.QDialog):
    
    lineFromStdOut = QtCore.Signal(str)
    
    def __init__(self, conda_dir):
        QtGui.QDialog.__init__(self)
        self.setModal(True)
        self.resize(500, 500)
        self._conda_dir = conda_dir
        
        text = 'This will download and install miniconda on your computer.'
        
        self._label = QtGui.QLabel(text, self)
        
        self._scipystack = QtGui.QCheckBox('Also install scientific packages', self)
        self._scipystack.setChecked(True)
        self._path = QtGui.QLineEdit(self._conda_dir, self)
        self._progress = QtGui.QProgressBar(self)
        self._outputLine = QtGui.QLabel(self)
        self._output = QtGui.QPlainTextEdit(self)
        self._output.setReadOnly(True)
        self._button = QtGui.QPushButton('Install', self)
        
        self._outputLine.setSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Fixed)
        
        vbox = QtGui.QVBoxLayout(self)
        self.setLayout(vbox)
        vbox.addWidget(self._label, 0)
        vbox.addWidget(self._path, 0)
        vbox.addWidget(self._scipystack, 0)
        vbox.addWidget(self._progress, 0)
        vbox.addWidget(self._outputLine, 0)
        vbox.addWidget(self._output, 1)
        vbox.addWidget(self._button, 0)
        
        self._button.clicked.connect(self.go)
        
        self.addOutput('Waiting to start installation.\n')
        self._progress.setVisible(False)
        
        self.lineFromStdOut.connect(self.setStatus)
        # todo: add a shell config for the created env
    
    
    def setStatus(self, line):
        self._outputLine.setText(line)
    
    def addOutput(self, text):
        #self._output.setPlainText(self._output.toPlainText() + '\n' + text)
        cursor = self._output.textCursor()
        cursor.movePosition(cursor.End, cursor.MoveAnchor)
        cursor.insertText(text)
        cursor.movePosition(cursor.End, cursor.MoveAnchor)
        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()
    
    def addStatus(self, line):
        self.addOutput('\n' + line)
        self.setStatus(line)
    
    def go(self):
        
        # Check if we can install
        try:
            self._conda_dir = self._path.text()
            if not os.path.isabs(self._conda_dir):
                raise ValueError('Given installation path must be absolute.')
            # if os.path.exists(self._conda_dir):
            #     raise ValueError('The given installation path already exists.')
        except Exception as err:
            self.addOutput('\nCould not install:\n' + str(err))
            return
        
        ok = False
        
        try:
            
            # Disable user input, get ready for installation
            self._progress.setVisible(True)
            self._button.clicked.disconnect()
            self._button.setEnabled(False)
            self._scipystack.setEnabled(False)
            self._path.setEnabled(False)
            
            if not os.path.exists(self._conda_dir):
                self.addStatus('Downloading installer ... ')
                self._progress.setMaximum(100)
                self.download()
                self.addStatus('Done downloading installer.')
                self.make_done()
                
                self.addStatus('Installing (this can take a minute) ... ')
                self._progress.setMaximum(0)
                ret = self.install()
                self.addStatus(('Failed' if ret else 'Done') + ' installing.')
                self.make_done()
            
            if self._scipystack.isChecked():
                self.addStatus('Installing scientific packages ... ')
                self._progress.setMaximum(0)
                ret = self.install_scipy()
                self.addStatus('Done installing scientific packages')
                self.make_done()
            
            self.addStatus('Verifying ... ')
            self._progress.setMaximum(100)
            ret = self.verify()
            if ret:
                self.addOutput('Error\n' + ret)
                self.addStatus('Verification Failed!')
            else:
                self.addOutput('Done verifying')
                self.addStatus('Ready to go!')
                self.make_done()
                ok = True
        
        except Exception as err:
            raise
            self.addStatus('Installation failed ...')
            self.addOutput('\n\nException!\n' + str(err))
        
        if not ok:
            self.addOutput('\n\nWe recommend installing miniconda or anaconda, ')
            self.addOutput('and making IEP aware if it via the shell configuration.')
        else:
            self.addOutput('\n\nYou can install additional packages by running "conda install" in the shell.')
        
        # Wrap up, allow user to exit
        self._progress.hide()
        self._button.setEnabled(True)
        self._button.setText('Close')
        self._button.clicked.connect(self.close)
    
    def make_done(self):
        self._progress.setMaximum(100)
        self._progress.setValue(100)
        etime = time.time() + 0.2
        while time.time() < etime:
            time.sleep(0.01)
            QtGui.qApp.processEvents()
    
    def download(self):
        # todo: _fetch_file()
        
        # Smooth toward 100%
        for i in range(0, 100, 5):
            time.sleep(0.1)
            self._progress.setValue(i)
            QtGui.qApp.processEvents()

    def install(self):
        dest = self._conda_dir
        
        # Clear dir 
        assert not os.path.isdir(dest), 'Miniconda dir already exists'
        assert ' ' not in dest, 'miniconda dest path must not contain spaces'
        
        # Get where we want to put miniconda installer
        miniconda_path = os.path.join(paths.appdata_dir('iep'), 'miniconda')
        miniconda_path += sys.platform.startswith('win') * '.exe'
        
        # Get fresh installer
        if os.path.isfile(miniconda_path):
            os.remove(miniconda_path)
        download_miniconda(miniconda)
        
        miniconda_path = miniconda  # todo: remove
        
        if sys.platform.startswith('win'):
            cmd = [miniconda_path, '/S', '/D=%s' % dest]
            return self._run_process(cmd)
        
        return p.poll()
    
    def post_install(self):
        pass
        # todo: set condarc to add pyzo channel
        # todo: add to config
        
    def install_scipy(self):
        
        packages = ['numpy', 'scipy', 'pandas', 'matplotlib',
                    #'scikit-image', 'scikit-learn',
                    #'ipython', 'jupyter',
                    'pytest', ]
        exe = py_exe(self._conda_dir)
        cmd = [exe, '-m', 'conda', 'install', '--yes'] + packages
        return self._run_process(cmd)
    
    def _run_process(self, cmd):
        """ Run command in a separate process, catch stdout, show lines
        in the output label. On fail, show all output in output text.
        """
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        catcher = StreamCatcher(p.stdout, self.lineFromStdOut)
        
        while p.poll() is None:
            time.sleep(0.01)
            QtGui.qApp.processEvents()
        
        catcher.join()
        if p.poll():
            self.addOutput(catcher.output())
        return p.poll()
    
    def verify(self):
        
        self._progress.setValue(1)
        if not os.path.isdir(self._conda_dir):
            return 'Conda dir not created.'
        
        self._progress.setValue(11)
        exe = py_exe(self._conda_dir)
        if not os.path.isfile(exe):
           return 'Conda dir does not have Python exe' 
        
        self._progress.setValue(21)
        try:
            ver = subprocess.check_output([exe, '-c', 'import sys; print(sys.version)'])
        except Exception as err:
            return 'Error getting Python version: ' + str(err)
        
        self._progress.setValue(31)
        if ver.decode() < '3.4':
            return 'Expected Python version 3.4 or higher'
        
        self._progress.setValue(41)
        try:
            ver = subprocess.check_output([exe, '-c', 'import conda; print(conda.__version__)'])
        except Exception as err:
            return 'Error calling Python exe: ' + str(err)
        
        self._progress.setValue(51)
        if ver.decode() < '3.16':
            return 'Expected Conda version 3.16 or higher'
        
        # Smooth toward 100%
        for i in range(self._progress.value(), 100, 5):
            time.sleep(0.05)
            self._progress.setValue(i)
            QtGui.qApp.processEvents()



def _chunk_read(response, local_file, chunk_size=4096, initial_size=0):
    """Download a file chunk by chunk and show advancement

    Can also be used when resuming downloads over http.

    Parameters
    ----------
    response: urllib.response.addinfourl
        Response to the download request in order to get file size.
    local_file: file
        Hard disk file where data should be written.
    chunk_size: integer, optional
        Size of downloaded chunks. Default: 4096
    initial_size: int, optional
        If resuming, indicate the initial size of the file.
    """
    # Adapted from NISL:
    # https://github.com/nisl/tutorial/blob/master/nisl/datasets.py

    bytes_so_far = initial_size
    # Returns only amount left to download when resuming, not the size of the
    # entire file
    total_size = int(response.headers['Content-Length'].strip())
    total_size += initial_size

    progress = QtGui.QProgressBar()
    progress.setMaximum(total_size)
    progress.show()
    

    while True:
        QtGui.qApp.processEvents()
        chunk = response.read(chunk_size)
        bytes_so_far += len(chunk)
        if not chunk:
            sys.stderr.write('\n')
            break
        #_chunk_write(chunk, local_file, progress)
        progress.setValue(bytes_so_far)
        local_file.write(chunk)



def _fetch_file(url, file_name, print_destination=True):
    """Load requested file, downloading it if needed or requested

    Parameters
    ----------
    url: string
        The url of file to be downloaded.
    file_name: string
        Name, along with the path, of where downloaded file will be saved.
    print_destination: bool, optional
        If true, destination of where file was saved will be printed after
        download finishes.
    resume: bool, optional
        If true, try to resume partially downloaded files.
    """
    # Adapted from NISL:
    # https://github.com/nisl/tutorial/blob/master/nisl/datasets.py

    temp_file_name = file_name + ".part"
    local_file = None
    initial_size = 0
    try:
        # Checking file size and displaying it alongside the download url
        response = urllib.request.urlopen(url, timeout=5.)
        file_size = int(response.headers['Content-Length'].strip())
        # Downloading data (can be extended to resume if need be)
        local_file = open(temp_file_name, "wb")
        _chunk_read(response, local_file, initial_size=initial_size)
        # temp file must be closed prior to the move
        if not local_file.closed:
            local_file.close()
        shutil.move(temp_file_name, file_name)
        if print_destination is True:
            sys.stdout.write('File saved as %s.\n' % file_name)
    except Exception as e:
        raise RuntimeError('Error while fetching file %s.\n'
                           'Dataset fetching aborted (%s)' % (url, e))
    finally:
        if local_file is not None:
            if not local_file.closed:
                local_file.close()


class StreamCatcher(threading.Thread):

    def __init__(self, file, signal):
        self._file = file
        self._signal = signal
        self._lines = []
        self._line = ''
        threading.Thread.__init__(self)
        self.setDaemon(True)  # do not let this thread hold up Python shutdown
        self.start()
    
    def run(self):
        while True:
            time.sleep(0.0001)
            try:
                part = self._file.read(20)
            except ValueError:  # pragma: no cover
                break
            if not part:
                break
            part = part.decode('utf-8', 'ignore')
            
            self._line += part.replace('\r', '\n')
            lines = [line for line in self._line.split('\n') if line]
            self._lines.extend(lines[:-1])
            self._line = lines[-1]
            
            if self._lines:
                self._signal.emit(self._lines[-1])
        
        self._lines.append(self._line)
        self._signal.emit(self._lines[-1])

    def output(self):
        return '\n'.join(self._lines)


if __name__ == '__main__':
    
    check_our_conda()#('c:\\miniconda_test')
