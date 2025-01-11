"""Simple script to make a performance plot of the speed for sending
different package sizes.
"""

# Go up one directory and then import the codeeditor package
import os
import sys

os.chdir("../..")
sys.path.insert(0, ".")

# Import yoton from there
import yoton

# Normal imports
import time

## Run experiment with different message sizes

# Setup host
ct1 = yoton.Context()
ct1.bind("localhost:test")
c1 = yoton.PubChannel(ct1, "speedTest")

# Setup client
ct2 = yoton.SimpleSocket()
ct2.connect("localhost:test")
c2 = yoton.SubChannel(ct2, "speedTest")

# Init
minSize, maxSize = 2, 100 * 2**20
BPS = []
TPM = []
N = []
SIZE = []


# Loop
size = minSize
while size < maxSize:
    # Calculate amount
    n = int(200 * 2**20 / size)
    n = min(yoton.core.BUF_MAX_LEN, n)

    t0 = time.time()

    # Send messages
    message = "T" * int(size)
    for i in range(n):
        c1.send(message)
    ct1.flush(20.0)

    t1 = time.time()

    # In the mean while two threads are working their asses off to pop
    # the packages from one queue, send them over a socket, and push
    # them on another queue.

    # Receive messages
    for i in range(n):
        c2.recv()

    t2 = time.time()

    # Calculate speed
    etime = t2 - t0
    bps = n * size / etime  # bytes per second
    tpm = etime / n

    # Make strings
    bps_ = "%1.2f B/s" % bps
    size_ = "%i B" % size
    #
    D = {2**10: "KB", 2**20: "MB", 2**30: "GB"}
    for factor in D:
        if bps >= factor:
            bps_ = "%1.2f %s/s" % (bps / factor, D[factor])
        if size >= factor:
            size_ = "%1.2f %s" % (size / factor, D[factor])

    # Show result
    print("Sent %i messages of %s in %1.2f s: %s" % (n, size_, etime, bps_))

    # Store stuff
    N.append(n)
    SIZE.append(size)
    BPS.append(bps)
    TPM.append(tpm)

    # Prepare for next round
    size *= 1.9


## Visualize

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

plt.ion()

fig, (ax1, ax2) = plt.subplots(2, 1, num=10, clear=True, sharex=True)


def format_si(value, unit):
    prefixes = ["micro", "m", "", "k", "M", "G"]
    i3 = int(np.log10(value) // 3)
    i = i3 + prefixes.index("")
    i = max(0, min(i, len(prefixes) - 1))
    multiplier = 10 ** (3 * i3)
    return "{:.0f} {}{}".format(value / multiplier, prefixes[i], unit)


formatter = FuncFormatter(lambda val, tick_pos: format_si(val, ""))

ax1.loglog(SIZE, BPS, ".")
ax1.set_ylabel("speed [bytes/s]")
ax2.loglog(SIZE, TPM, ".")
ax2.set_ylabel("time per message [s]")
ax2.set_xlabel("message size [bytes]")

ax2.xaxis.set_major_formatter(formatter)
ax2.tick_params("x", rotation=45)

for ax in [ax1, ax2]:
    ax.grid(True)
    ax.yaxis.set_major_formatter(formatter)

fig.tight_layout()

# fig.savefig("yoton_performance.jpg")
