#! /usr/bin/env python3
# dtcli.py  22/01/2023  D.J.Whale - data transfer command line interface
# NOTE: for use on HOST python only

import sys
import ftag_host as ftag
import dttk

link_manager = ftag.dttk.LinkManager(dttk.StdStreamRadio())

#----- SENDER ------------------------------------------------------------------

def do_send(argv) -> None:
    """Parse args and send a file"""
    parsed_args = parse_send_args(argv)
    run_send(**parsed_args)

def parse_send_args(argv) -> dict:
    """Parse --send args to a dict"""
    filename = None
    progress = False
    for arg in argv:
        if arg == '-p':         progress = True
        elif filename is None:  filename = arg

    if filename is None:
        exit("usage: dtcli.py --send [-p] <filename>")

    return {"filename": filename, "progress": progress}

def run_send(filename:str, progress:bool=False) -> None:
    """Send a file using packetiser and std streams"""
    #NOTE: progress flag not supported currently
    sender = ftag.send_file_task(filename, link=link_manager)
    sender.run()
    ftag.print_stats("tx", sender)

#----- RECEIVER ----------------------------------------------------------------

def do_receive(argv) -> None:
    """Parse args and receive a file"""
    parsed_args = parse_receive_args(argv)
    run_receive(**parsed_args)

def parse_receive_args(argv) -> dict:
    """Parse --receive args to a dict"""
    filename = None
    progress = False
    for arg in argv:
        if arg == '-p':         progress = True
        elif filename is None:  filename = arg

    if filename is None:
        exit("usage: dtcli.py --receive [-p] <filename>")

    return {"filename": filename, "progress": progress}

def run_receive(filename:str, progress:bool=False):
    """Receive a file using packetiser and std streams"""
    #NOTE: progress flag not supported currently
    receiver = ftag.receive_file_task(filename, link=link_manager)
    receiver.run()
    ftag.print_stats("rx", receiver)

#----- BIN2HEX -----------------------------------------------------------------

def do_bin2hex(argv) -> None:
    """No args, just run bin2hex"""
    bin2hex()

def bin2hex() -> None:
    """Run bin2hex to convert incoming binary stream into an outgoing hexascii"""
    recv_bin      = ftag.dttk.StreamReader(sys.stdin.buffer).read
    send_hex_line = ftag.dttk.HexStreamWriter(sys.stdout.buffer).write

    while True:
        # read binary data from stdin
        data = recv_bin()
        if data is None: break  # EOF

        # write it as hexascii to stdout
        send_hex_line(data)

#----- HEX2BIN -----------------------------------------------------------------

def do_hex2bin(argv) -> None:
    """No args, just run hex2bin"""
    hex2bin()

def hex2bin() -> None:
    """Run hex2bin to convert incoming hexascii into binary"""
    recv_hex_line = ftag.dttk.HexStreamReader(sys.stdin.buffer).read
    send_bin = ftag.dttk.StreamWriter(sys.stdout.buffer).write

    while True:
        # read hexascii data from stdint
        data = recv_hex_line()
        if data is None: break  # EOF

        # write binary data to stdout
        send_bin(data)

#----- NOISE -------------------------------------------------------------------

DEFAULT_PACKET_LEN = 32

def do_noise(argv) -> None:
    """Parse --noise args and run noise generator"""
    spec = parse_noise_args(argv)
    run_noise(spec)

def parse_noise_args(argv) -> dict:
    """Parse --noise args to a dict"""
    #   --len=32      packet size
    #   --edrop=50    50% chance of dropping a packet of packet size bytes
    #   --elen=-4,2   length errors(trunc,extend)
    #   --ebit=5,9    bit errors(num, dist)
    #   --ebyte=2,4   byte errors(num, dist)
    #   --prob=12     12 % probability of a duff packet
    #   -p            predictable (non random)

    spec = {}

    for arg in argv:
        if not arg.startswith("--"):
            exit("unknown arg:%s" % arg)

        ##if arg == "-p":  #NOTE: not yet handled
        ##    spec["predictable"] = True

        if arg.startswith("--len="):
            v = arg[6:]
            try:
                spec["packet_len"] = int(v)
            except:
                exit("invalid value:%s" % arg)

        elif arg.startswith("--prob="):
            v = arg[7:]
            try:
                prob = int(v)
                spec["prob"] = prob
            except:
                exit("invalid value:%s" % arg)

        elif arg.startswith("--edrop="):
            v = arg[8:]
            try:
                drop_perc = int(v)
                spec["drop"] = drop_perc
            except:
                exit("invalid value:%s" % arg)

        elif arg.startswith("--elen="):
            v = arg[7:]
            try:
                trunc, extend = v.split(',')
                trunc = int(trunc)
                extend = int(extend)
                spec["len"] = (trunc, extend)
            except:
                exit("invalid value:%s" % arg)

        elif arg.startswith("--ebit="):
            v = arg[7:]
            try:
                num, dist = v.split(',')
                num = int(num)
                dist = int(num)
                spec["bit"] = (num, dist)
            except:
                exit("invalid value:%s" % arg)

        elif arg.startswith("--ebyte="):
            v = arg[8:]
            try:
                num, dist = v.split(',')
                num = int(num)
                dist = int(dist)
                spec["byte"] = (num, dist)
            except:
                exit("invalid value:%s" % arg)

        else:
            exit("unknown arg:%s" % arg)

    return spec

def run_noise(spec:dict) -> None:
    """Run noise generator by reading stdin(bin) and writing stdout(bin)"""
    if "packet_len" in spec:
        packet_len = spec["packet_len"]
    else:
        packet_len = DEFAULT_PACKET_LEN

    add_noise = ftag.dttk.NoiseGenerator(spec).send

    while True:
        # read data
        data = sys.stdin.buffer.read(packet_len)  # bytes
        eof = len(data) != packet_len

        # apply errors
        noisy_data = add_noise(data)

        # write data
        sys.stdout.buffer.write(noisy_data)
        sys.stdout.flush()

        if eof: break

#===== MAIN ====================================================================

def usage(msg:str or None=None) -> None:
    """Display a helpful usage message"""
    if msg is not None: print(msg)
    print("usage: ftcli --send <filename> [-p]")
    print("       ftcli --receive <filename> [-p]")
    print("       ftcli --hex2bin")
    print("       ftcli --bin2hex")
    print("       ftcli --noise <noise-args>")

def main(argv) -> None:
    """Main program"""
    if len(argv) == 0:
        usage()
        exit(1)

    tool_name = argv[0]
    argv = argv[1:]  # shift

    try:
        # dispatch to tool
        if   tool_name == "--send":    do_send(argv)
        elif tool_name == "--receive": do_receive(argv)
        elif tool_name == "--hex2bin": do_hex2bin(argv)
        elif tool_name == "--bin2hex": do_bin2hex(argv)
        elif tool_name == "--noise":   do_noise(argv)
        else:
            usage("unknown tool:%s" % str(tool_name))
            exit(1)

    except BrokenPipeError:
        sys.stderr.write("%s: broken pipe\n" % tool_name[2:])
    ##except KeyboardInterrupt:
    ##    sys.stderr.write("\n%s: CTRL-C\n" % tool_name[2:])

if __name__ == "__main__":
    main(sys.argv[1:])

#END: dtcli.py
