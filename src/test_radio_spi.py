# test_radio_spi.py  11/02/2023  D.J.Whale - test RFM69 radio on SPI0

from machine import SPI, Pin
from utime import sleep_ms, sleep_us

RADIO_SPEED_HZ = 400_000
RADIO_SPI_N    = 0
RADIO_G0_GPN   = 0  # {GP0}/TX0/SDA0/DIO/PWM0A
RADIO_CS_GPN   = 1  # {GP1}/RX0/SCL0/CS0/PWM0B
RADIO_SCK_GPN  = 2  # GP2/SDA1/{SCK0}/PWM1A
RADIO_MOSI_GPN = 3  # GP3/SCL1/DO0/PWM1B
RADIO_MISO_GPN = 4  # GP4/TX1/SDA0/{DI0}/PWM2A
RADIO_RES_GPN  = 6  # {GP6}/SDA1/SCK0/PWM3A
RADIO_EN_GPN   = 7  # {GP7}/SCL1/DO0/PWM3B

spi = SPI(RADIO_SPI_N, baudrate=RADIO_SPEED_HZ, polarity=0, phase=0, bits=8,
          sck=Pin(RADIO_SCK_GPN), mosi=Pin(RADIO_MOSI_GPN), miso=Pin(RADIO_MISO_GPN))

# chip select idles high when bus inactive
spi_cs = Pin(RADIO_CS_GPN, Pin.OUT)
spi_cs.high()  # deselected
print("CS idle high")

# reset pin is normally low in normal operation
res = Pin(RADIO_RES_GPN, Pin.OUT)
res.low()
print("RES idle low")

# EN pin will float high, but experiments show it needs a hard pull up
# and this turns on the regulator on the RFM69HCW baseboard
radio_en = Pin(RADIO_EN_GPN, Pin.OUT)
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
    res = bytearray(len(data))
    spi_cs.low()  # select
    spi.write_readinto(data, res)
    spi_cs.high()  # deselect
    print("tx done")
    return res

def readreg(addr: int) -> int:
    """Use this to read any radio register"""
    return xfer(bytearray((addr, 0)))[1]

def test():
    """Use this to test the radio responds"""
    R_VERSION = 0x10  # register to read
    EXPECTED = 0x24   # value to expect back for a PASS
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

