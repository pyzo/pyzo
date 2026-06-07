import sys
import signal
import yoton


if sys.version_info[0] < 3:
    import thread
else:
    import _thread as thread


class PyzoKernelControl(yoton.RepChannel):
    """This is a RepChannel object that runs a thread to control the kernel from the IDE."""

    def interrupt(self, command=None, signum=signal.SIGINT):
        """Interrupt the main thread.

        This does not work if the main thread is running extension code.

        Note that on POSIX we can send an OS INT signal, which is faster
        and maybe more effective in some situations.

        signum must be signal.SIGINT for kernels running Python < 3.10
        """
        if signum == signal.SIGINT:
            thread.interrupt_main()
        else:
            if sys.version_info < (3, 10):
                print("This feature is not implemented for Python versions < 3.10!")
                return
            thread.interrupt_main(signum)

    def terminate(self, command=None):
        """terminate()

        Ask the kernel to terminate by closing the stdin.

        """
        sys.stdin._channel.close()
