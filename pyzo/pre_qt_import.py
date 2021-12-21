import os


# Automatically scale along on HDPI displays. See issue #531 and e.g.
# https://wiki.archlinux.org/index.php/HiDPI#Qt_5
if "QT_AUTO_SCREEN_SCALE_FACTOR" not in os.environ:
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

# Fix Qt now showing a window on MacOS Big Sur
os.environ["QT_MAC_WANTS_LAYER"] = "1"
