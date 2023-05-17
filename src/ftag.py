# ftag.py  06/02/2023  D.J.Whale - File Transfer Agent

import os
import dttk
import tasking

# detect which platform we are running on
try:
    import utime
    # we are on Pico
    from ftag_pico import *

except ImportError:
    ##print(e)
    # we are on Host
    from ftag_host import *

TX_FILENAME = "test35k.jpg"
RX_FILENAME = "received.jpg"

def show_dir(dir_name:str, dir_path:str) -> None:
    print("directory of:%s" % dir_name)
    for name in os.listdir(dir_path):
        print("  ", name)

def files() -> None:
    show_dir("cwd", ".")

def help() -> None:
    print("FTAG File Transfer Agent demonstrator")
    print("  ftag.help()     - show this help message")
    print("  ftag.files()    - list files in local file system")
    print("  ftag.loopback() - send and receive via UART0 loopback")
    print("  ftag.send()     - send a test file via UART0")
    print("  ftag.receive()  - receive a test file via UART0")

#Throttled send, by default.
DEFAULT_PPS = 40  # experimental evidence shows this keeps a 512+32 receive ok
def send(filename:str=TX_FILENAME, pps:int=DEFAULT_PPS, progress=None) -> None:
    #TODO: throttling should be an option in sender, so loopback can use it too
    print("sending:%s" % filename)
    sender = send_file_task(filename, progress=progress)
    if pps is not None:
        print("  throttled at %d PPS" % pps)
        while True:
            start_ms = platdeps.time_ms()
            if not sender.tick(): break  # finished
            if pps is not None:
               time_per_packet_ms = platdeps.time_ms() - start_ms
               delay_time_ms = int((1000 - (time_per_packet_ms * pps)) / pps)
               platdeps.time_sleep_ms(delay_time_ms)
    else:
        sender.run()

    print_stats("tx", sender)
    print("send complete")

def receive(filename:str=RX_FILENAME, progress=None) -> None:
    print("receiving:%s" % filename)
    receiver = receive_file_task(filename, progress=progress)
    receiver.run()

    print_stats("rx", receiver)

    print("receive complete")

def loopback(tx_filename:str=TX_FILENAME, rx_filename:str=RX_FILENAME,
             tx_progress=None, rx_progress=None) -> None:
    print("loopback %s->%s running" % (tx_filename, rx_filename))
    sender   = send_file_task(tx_filename, progress=tx_progress)
    receiver = receive_file_task(rx_filename, progress=rx_progress)

    tasking.run_all([sender, receiver])

    #TEST CODE
    # # show task progress, so we can spot lockups
    # s = True
    # r = True
    # while s or r:
    #     if s:
    #         print("send")
    #         s = sender.tick()
    #     if r:
    #         print("recv")
    #         r = receiver.tick()

    print_stats("tx", sender)
    print_stats("rx", receiver)

    print("loopback complete")

if __name__ == "__main__":
    # for host-only testing
    import sys
    if len(sys.argv) < 3:
        exit("usage: ftag <tx_filename> <rx_filename>  - loopback testing")
    tx_filename = sys.argv[1]
    rx_filename = sys.argv[2]
    loopback(tx_filename, rx_filename)

#END: ftag.py
