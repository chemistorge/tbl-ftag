# main.py  11/02/2023  D.J.Whale

import myboard
from radio import RadioISM
from utime import sleep_ms
from dttk import Buffer  #TODO: try to remove this dependency from tester

TX_DELAY_MS = 500
RX_DELAY_MS = 50
radio = RadioISM()

def hexstr(data) -> str:
    """generate a run of bytes as a hexascii string"""
    if data is None: return ""
    res = []
    for b in data:
        res.append("%02X" % b)
    return " ".join(res)

def textstr(data) -> str:
    """generate a run of bytes as an ascii text string"""
    if data is None: return ""
    res = []
    for b in data:
        if b < 32 or b > 127:
            res.append("[%02X]" % b)
        else:
            res.append("%c" % chr(b))
    return " ".join(res)

def test_radio_send():
    #          .........!.........!.........!.........!.........!.........!12345
    TEXT65 = b'01234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz@*'

    SIZE    = radio.MTU-1  # always sends count-byte preceeded
    ##buffer      = bytearray(SIZE)
    ##buffer[0]   = SIZE
    ##buffer[1:]  = TEXT65[:SIZE]

    buffer = Buffer()
    buffer.append(SIZE)
    buffer.extend(TEXT65[:SIZE])

    print("test_send()")
    counter = 0
    while True:
        counter += 1
        print("tx[%d]: %d %d" % (counter, radio.BAUD_RATE, len(buffer)))
        radio.send(buffer)
        sleep_ms(TX_DELAY_MS)

def test_radio_recv():
    """Receive a raw payload and print it"""
    print("test_recv()")
    ##buffer = bytearray(radio.MTU)
    buffer = Buffer()

    radio.always_receive()
    myboard.rx_led_pin(0)
    counter = 0

    while True:
        nb = radio.recvinto(buffer)
        rssi = radio.get_rssi()
        if rssi is None: rssi = "(NO_RSSI)"
        if nb is not None and nb > 0:
            counter += 1
            ##raw_msg = memoryview(buffer)[0:nb]
            raw_msg = buffer[0:nb]

            myboard.rx_led_pin(1)
            print("rx[%d]: BR:%d, RSSI:%s, len:%d" % (counter, radio.BAUD_RATE, rssi, len(raw_msg)))
            print("hex:", hexstr(raw_msg[:]))
            print("txt:", textstr(raw_msg[:]))

            sleep_ms(RX_DELAY_MS)
            myboard.rx_led_pin(0)
            buffer.reset()

def test_radio():
    try:
        print("BAUD_RATE:%d (%04X)" % (radio.BAUD_RATE, radio.BAUD_WORD))
        radio.on()

        if myboard.OPTION:
            test_radio_send()
        else:
            test_radio_recv()
    finally:
        radio.off()

print("test_radio: test radio transmit and receive")
print("GP16=1 for sender, GP16=0 for receiver")
print("test_radio() - to run the appropriate test")
