from remote2 import IepInterpreter, IntroSpectionThread
from channels import Channels
import sys
import __main__ # we will run code in the __main__.__dict__ namespace

# process input args (if it fails, well an exception is raised...)
port = int(sys.argv[1])

# set no input arguments (do keep the first)
sys.argv[1:] = []

# make connection object and get channels
c = Channels(4)
sys.stdin = c.getReceivingChannel(0)
sys.stdout = c.getSendingChannel(0)
sys.stderr = c.getSendingChannel(1)
sys._status = c.getSendingChannel(2)

# connect
c.connect(port, timeOut=1)

# create interpreter instance
__iep__ = IepInterpreter(locals=__main__.__dict__)
__iep__.channels = c

# create introspection thread instance
__iep__.ithread = IntroSpectionThread(  
    c.getReceivingChannel(1), c.getSendingChannel(3), __main__.__dict__)


# todo: need more cleaning up?
del IepInterpreter
__iep__.ithread.start()
__iep__.interact()
