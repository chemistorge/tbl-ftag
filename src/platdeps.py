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
    os_path_splitext = os.path.splitext
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

    def basename(path: str) -> str:
        slash_pos = path.rfind("/")
        if slash_pos != -1: return path[slash_pos + 1:]
        return path

    def splitext(path: str) -> tuple:  # (str, str)
        """Split into path, extn - implements os.path.splitext"""
        dot_pos = path.rfind(".")
        if dot_pos == -1: return path, ""  #  no extension

        # found a dot, might be an extension, is it more left than any slash
        slash_pos = path.rfind("/")

        # if no slash, this dot must be part of the filename part
        if slash_pos == -1: return path[:dot_pos], path[dot_pos:]

        # there is a slash, is the dot left of the slash
        if dot_pos < slash_pos: return path, ""  # no extension
        return path[:dot_pos], path[dot_pos:]  # there is an extension


    time_time        = utime.time      # seconds, int
    time_perf_time   = utime.ticks_us  # us, int
    time_ms          = utime.ticks_ms  # ms, int
    time_sleep_ms    = utime.sleep_ms  # ms, int
    os_path_basename = basename
    os_path_splitext = splitext
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
