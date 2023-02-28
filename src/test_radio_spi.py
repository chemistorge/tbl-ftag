# test_radio_spi.py  11/02/2023  D.J.Whale - test RFM69 radio on SPI0

from machine import SPI, Pin
from utime import sleep_ms, sleep_us

SPEED_HZ = 400_000
SPI_N = 0

GP_G0 = 0  # input
GP_CS = 1  # output
GP_SCK = 2  # output
GP_MOSI = 3  # output
GP_MISO = 4  # input
GP_RES = 6  # output (low for run)
GP_EN = 7  # output (enable power supply or leave disconnected for on)

spi = SPI(SPI_N, baudrate=SPEED_HZ, polarity=0, phase=0, bits=8,
          sck=Pin(GP_SCK), mosi=Pin(GP_MOSI), miso=Pin(GP_MISO))

# chip select idles high when bus inactive
spi_cs = Pin(GP_CS, Pin.OUT)
spi_cs.high()  # deselected
print("CS idle high")

# reset pin is normally low in normal operation
res = Pin(GP_RES, Pin.OUT)
res.low()
print("RES idle low")

# EN pin will float high, but experiments show it needs a hard pull up
# and this turns on the regulator on the RFM69HCW baseboard
radio_en = Pin(GP_EN, Pin.OUT)
radio_en.high()
print("EN idle high")

def test_pin(pin_no: int, name:str=None):
    """Use this for individual pin verification"""
    if name is None: name = "GP%d" % pin_no
    print("test_pin:%s %d" % (name, pin_no))
    p = Pin(pin_no, Pin.OUT)
    for _ in range(8):
        p.high()
        sleep_ms(250)
        p.low()
        sleep_ms(250)

def reset():
    """Use this to test the reset pulse"""
    print("resetting")
    res.high()
    sleep_ms(150)
    res.low()
    sleep_us(100)
    print("resetting done")

def xfer(data: bytes):
    """Use this to send and receive, for register access"""
    print("tx")
    spi_cs.low()  # select
    res = bytearray(len(data))
    spi.write_readinto(data, res)
    spi_cs.high()  # deselect
    print("tx done")
    return res

def readreg(addr: int) -> int:
    """Use this to read any radio register"""
    return xfer(bytearray((addr, 0)))[1]

def test():
    """Use this to test the radio responds"""
    R_VERSION = 0x10
    EXPECTED = 0x24
    reset()
    actual = readreg(R_VERSION)
    if EXPECTED != actual:
        print("FAIL: expected:%02X got:%02X" % (EXPECTED, actual))
    else:
        print("PASS: version=%02X" % actual)

print("test_radio_spi program")
print("reset()      - generate reset pulse")
print("test_pin(3)  - toggle-test a GP pin, any number allowed")
print("test()       - does the radio respond with correct version no?")

