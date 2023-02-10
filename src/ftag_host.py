# ftag_host.py  22/01/2023  D.J.Whale - host based adaptor to file transfer agent
#NOTE: for use on HOST python only

import sys
import time
import os
import hashlib
import dttk

class CPythonDeps:
    time_time        = time.time  # seconds&ms, float
    time_perf_time   = time.time  # seconds&ms, float
    time_ms          = lambda: int(time.time()*1000)  # milliseconds
    time_sleep_ms    = lambda ms: time.sleep(ms/1000.0)
    os_path_basename = os.path.basename
    os_rename        = os.rename
    os_unlink        = os.unlink
    filesize         = lambda filename: os.stat(filename).st_size
    hashlib_sha256   = hashlib.sha256
    message          = lambda msg: sys.stderr.write(msg + '\n')
    decode_to_str    = lambda b: b.decode(errors='ignore')

dttk.set_deps(CPythonDeps)

default_link_manager = dttk.LinkManager(dttk.InMemoryRadio())


#IDEA: when we start a new file transfer task, we should establish and get next channel
#in the task start process

#txp = dttk.Progresser("tx").update
#tx_bar = dttk.ProgressBar()

# def tx_progress(msg:str or None=None, value:int or None=None) -> None:
#     if value is not None and msg is not None:
#         tx_bar.set_value(value)
#         msg = "%s %s" % (str(tx_bar), msg)
#     txp(msg)
tx_progress = None

rxp = dttk.Progresser("rx").update
rx_bar = dttk.ProgressBar()

def rx_progress(msg:str or None=None, value:int or None=None) -> None:
    if value is not None and msg is not None:
        rx_bar.set_value(value)
        msg = "%s %s" % (str(rx_bar), msg)
    rxp(msg)
##rx_progress = None


#----- TRANSFER TASKS ----------------------------------------------------------
def send_file_task(filename:str, link=None) -> dttk.Sender: # or exception
    """Non-blocking sender for a single file (as a task that has a tick())"""
    if link is None: link = default_link_manager
    return dttk.FileSender(filename, link, progress_fn=tx_progress, blocksz=50)

def receive_file_task(filename:str, link=None) -> dttk.Receiver: # or exception
    """Non-blocking receiver"""
    if link is None: link = default_link_manager
    #NOTE: cached mode is off on host, as there is no interference between the
    #file system and interupts on host
    return dttk.FileReceiver(link, filename, progress_fn=rx_progress, cached=False)

#NOTE: TO FIX
# def receive_file_noisy_task(filename:str) -> None: # or exception
#    """Non-blocking receiver with injected noise"""
#    raise ValueError("BROKEN SINCE LAST REFACTOR")
# NOISE_SPEC = {"prob": 1, "byte": (1,10)}
# noise_gen = dttk.NoiseGenerator(NOISE_SPEC).send
# def noisy_receive(info:dict or None=None) -> bytes or None:
#     return noise_gen(radio.recvinto(buf, info))
# receiver = dttk.FileReceiver(noisy_receive, filename, progress_fn=rx_progress)
# return receiver  # has-a tick() and run()

def print_stats(name:str, task) -> None:
    """Host-specific print_stats for sender or receiver"""
    CPythonDeps.message("stats for:%s" % name)
    CPythonDeps.message("  link:     %s" % str(dttk.link_stats))
    CPythonDeps.message("  pkt:      %s" % str(dttk.packetiser_stats))
    CPythonDeps.message("  transfer: %s" % task.get_stats())

#END: ftag_host.py

