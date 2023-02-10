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
# experiments show that about 11pps doesn't stress the receiver too much
def send(filename:str=TX_FILENAME, pps:int=11) -> None:
    print("sending:%s" % filename)
    sender = send_file_task(filename)
    if pps is not None:
        print("  throttled at %d PPS" % pps)
        while True:
            start_ms = dttk._deps.time_ms()
            if not sender.tick(): break  # finished
            if pps is not None:
               time_per_packet_ms = dttk._deps.time_ms() - start_ms
               delay_time_ms = int((1000 - (time_per_packet_ms * pps)) / pps)
               dttk._deps.time_sleep_ms(delay_time_ms)
    else:
        sender.run()

    print_stats("tx", sender)
    print("send complete")

def receive(filename:str=RX_FILENAME) -> None:
    print("receiving:%s" % filename)
    receiver = receive_file_task(filename)
    receiver.run()

    print_stats("rx", receiver)

    print("receive complete")

def loopback(tx_filename:str=TX_FILENAME, rx_filename:str=RX_FILENAME) -> None:
    print("loopback %s->%s running" % (tx_filename, rx_filename))
    sender   = send_file_task(tx_filename)
    receiver = receive_file_task(rx_filename)

    tasking.run_all([sender, receiver])

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
