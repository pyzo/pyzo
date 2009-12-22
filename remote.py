from remote2 import IepInterpreter
from channels import Channels
import sys

# process input args (if it fails, well an exception is raised...)
port = int(sys.argv[1])

# set no input arguments (do keep the first)
sys.argv[1:] = []

# make connection
c = Channels(4)
sys.stdin = c.getReceivingChannel(0)
sys.stdout = c.getSendingChannel(0)
sys.stderr = c.getSendingChannel(1)
sys._status = c.getSendingChannel(3)

c.connect(port, timeOut=1)

# class P:
#     def readOne(self,block=False):
#         return "print 'aap'"
#     @property
#     def closed(self):
#         return False
# sys.stdin = P()

# print 'hello1'
# import time
# while True:
#     line = sys.stdin.readOne(False)
#     if line:
#         print 'you asked: ' + line
#     if line=='stop':
#         break
#     time.sleep(0.1)
# print 'tot ziens'
import __main__
# create interpreter instance
locals = {'aap':'mies'} # todo: make this __main__.__dict__ (import __main__)
__iep__ = IepInterpreter(locals=__main__.__dict__)
__iep__.channels = c


# todo: need more cleaning up?
del IepInterpreter
__iep__.interact()
