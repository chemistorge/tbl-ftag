# ftag_host.py  22/01/2023  D.J.Whale - host based adaptor to file transfer agent
#NOTE: for use on HOST python only

import sys
import time
import os
import hashlib
import dttk

class HostDeps:
    TESTDATA         = "."
    time_time        = time.time  # seconds&ms, float
    time_perf_time   = time.time  # seconds&ms, float
    time_ms          = lambda: int(time.time()*1000)  # milliseconds
    time_sleep_ms    = lambda ms: time.sleep(ms/1000.0)
    os_path_basename = os.path.basename
    filesize         = lambda filename: os.stat(filename).st_size
    os_rename        = os.rename
    hashlib_sha256   = hashlib.sha256
    message          = lambda msg: sys.stderr.write(msg + '\n')
    decode_to_str    = lambda b: b.decode(errors='ignore')

dttk.set_deps(HostDeps)

radio = dttk.InMemoryRadio()
link_manager = dttk.LinkManager(radio)


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


#----- SENDERS -----------------------------------------------------------------
def send_file_task(filename:str) -> None: # or exception
    """Non-blocking sender for a single file (as a task that has a tick())"""
    return dttk.FileSender(filename, link_manager, progress_fn=tx_progress, blocksz=50)

def send_file(filename:str) -> None:  # or exception
    """Blocking sender for a single file"""
    send_file_task(filename).run()


#----- RECEIVERS ---------------------------------------------------------------
def receive_file_task(filename:str) -> None: # or exception
    """Non-blocking receiver"""
    return dttk.FileReceiver(link_manager, filename, progress_fn=rx_progress)

def receive_file_noisy_task(filename:str) -> None: # or exception
    """Non-blocking receiver with injected noise"""
    raise ValueError("BROKEN SINCE LAST REFACTOR")
    # NOISE_SPEC = {"prob": 1, "byte": (1,10)}
    # noise_gen = dttk.NoiseGenerator(NOISE_SPEC).send
    # def noisy_receive(info:dict or None=None) -> bytes or None:
    #     return noise_gen(radio.recvinto(buf, info))
    # receiver = dttk.FileReceiver(noisy_receive, filename, progress_fn=rx_progress)
    # return receiver  # has-a tick() and run()

def receive_file(filename:str) -> None:  # or exception
    """Blocking receiver for a single file"""
    receive_file_task(filename).run()
    ##print("<<LINK STATS:%s" % str(dttk.link_stats))
    ##print("<<PACKETISER STATS:%s" % str(dttk.packetiser_stats))

def receive_file_noisy(filename:str) -> None: # or exception
    """Blocking receiver for a single file, with injected noise"""
    receive_file_noisy_task(filename).run()


#END: ftag_host.py

