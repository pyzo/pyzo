"""
This is an example for using externally started shells with Pyzo.
Some third party software start their own Python interpreter process.
To use that Python process in a shell in Pyzo, just have Pyzo running
and then execute this code in the external Python interpreter.

For example, start a normal Python interpreter in a terminal resp. command window so that
you have an interactive Python session.
In this Python session, execute the following code lines:

fp = '/path/to/start_external_shell.py'
with open(fp, 'rt') as fd: pyzo_kernel_code = fd.read()
exec(pyzo_kernel_code)

This will create a shell in Pyzo's "Shells" panel. You can now use it like a shell that
was started inside Pyzo. To give back control to the external Python interpreter, just
close the shell inside Pyzo (via "Shell -> Close" in Pyzo's menu).
After closing the shell, you can start the Pyzo kernel again by executing
exec(pyzo_kernel_code)
again. All variables are still there because it is the same Python session.

A more real-world example, where external shells can be useful:
Run the software "Blender" -- https://en.wikipedia.org/wiki/Blender_(software)
and enter the code above in Blender's Python console to run the Pyzo kernel.
Now you can use Pyzo to perform commands as listed below, though the Blender GUI will
freeze till the shell is closed again. But you can re-enter the kernel anytime.
bpy.ops.mesh.primitive_cube_add(size=3, location=(0, 0, 0))
bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
# https://docs.blender.org/api/current/info_gotcha.html#can-i-redraw-during-script-execution
"""


def _run_pyzo_kernel():

    import os
    import sys
    import ast
    import socket
    import textwrap

    def send_data_to_pyzo_commandserver(shell_config):
        # TCP client
        remote_port = 63859  # port_hash('pyzoserver') --> 63859
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            try:
                sock.connect(('127.0.0.1', remote_port))
                sock.sendall('startexternalshell {!r}\r\n'.format(shell_config).encode('utf-8'))
                data = sock.recv(1024)
                answer = data.decode('utf-8')
                return answer
            except socket.timeout as e:
                print('could not connect to the pyzo commandserver')
                raise e

    def get_pyzo_shell_interface(shell_config):
        # TCP server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('127.0.0.1', 0))
            my_server_port = sock.getsockname()[1]
            sock.settimeout(5.0)
            sock.listen(1)

            shell_config['externalshell_callbackport'] = my_server_port
            answer = send_data_to_pyzo_commandserver(shell_config)
            if answer != 'ok\r\n':
                raise ValueError('invalid response from commandserver')

            sock_conn, addr = sock.accept()
            sock_conn.settimeout(5.0)
            data = sock_conn.recv(1024 * 8)
            sock_conn.close()

        port_string, pyzo_startscript_repr = data.decode('utf-8').strip().split(None, 1)
        fp_startscript = ast.literal_eval(pyzo_startscript_repr)
        return port_string, fp_startscript

    # os.environ['PYZO_PROCESS_EVENTS_WHILE_DEBUGGING'] = '1'

    shell_config = {
        'name': 'ext. shell',
        'gui': 'none',
        'pythonPath': '',
        'projectPath': '',
        'scriptFile': '',
        'startDir': '',
        'startupScript': textwrap.dedent("""
            # AFTER_GUI
            pass
        """.strip('\n')),
        'argv': '',
    }

    port_string, fp_startscript = get_pyzo_shell_interface(shell_config)

    cwd = os.path.dirname(os.path.dirname(fp_startscript))

    with open(fp_startscript, 'rt', encoding='utf-8') as fd:
        tt = fd.read()

    sys.path.append(cwd)
    sys.argv = [fp_startscript, port_string]
    exec(compile(tt, fp_startscript, 'exec'))


try:
    _run_pyzo_kernel()
except SystemExit:
    pass
finally:
    pass  # do some clean-up here if necessary
