# platdeps.py  16/03/2023  D.J.Whale - platform dependencies

# detect platform
MPY     = "mpy"
CPYTHON = "cpy"

try:
    import utime  # MicroPython
    PLATFORM = MPY

except ImportError:
    # we are on Host
    PLATFORM = CPYTHON

#----- CYPYTHON ----------------------------------------------------------------

if PLATFORM == CPYTHON:
    # scaffolding
    class micropython:
        # no viper, use this as a null decorator
        @staticmethod
        def viper(fn:callable) -> callable: return fn
    ptr8 = bytes
    ptr16 = bytes

    import time
    import os
    import hashlib
    import sys

    time_time        = time.time  # seconds&ms, float
    time_perf_time   = time.time  # seconds&ms, float
    time_ms          = lambda: int(time.time() * 1000)  # milliseconds
    time_sleep_ms    = lambda ms: time.sleep(ms / 1000.0)

    os_path_basename = os.path.basename
    os_rename        = os.rename
    os_unlink        = os.unlink
    filesize         = lambda filename: os.stat(filename).st_size
    hashlib_sha256   = hashlib.sha256

    message          = lambda msg: sys.stderr.write(msg + '\n')
    decode_to_str    = lambda b: b.decode(errors='ignore')

#----- MICRO PYTHON ------------------------------------------------------------
elif PLATFORM == MPY:
    import utime
    import os
    import uhashlib
    import micropython

    time_time        = utime.time      # seconds, int
    time_perf_time   = utime.ticks_us  # us, int
    time_ms          = utime.ticks_ms  # ms, int
    time_sleep_ms    = utime.sleep_ms  # ms, int
    os_path_basename = lambda p: p     #NOTE: TEMPORARY fix
    os_rename        = os.rename
    os_unlink        = os.remove
    filesize         = lambda filename: os.stat(filename)[6]
    hashlib_sha256   = uhashlib.sha256
    message          = print

    def decode_to_str(b:bytes) -> str:
        # There is no "errors='ignore'" on Pico
        try:
            return b.decode()
        # Pico throws UnicodeError, not UnicodeDecodeError
        except UnicodeError:
            print("unicode decode error")
            return "<UnicodeError>"  # this is the best we can do

#END: platdeps.py
