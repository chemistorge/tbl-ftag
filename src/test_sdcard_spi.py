# test_sd_spi.py  23/02/2023  D.J.Whale - test SD card on SPIn

from machine import SPI, Pin
from utime import sleep_ms, sleep_us

SPEED_HZ = 100_000
SPI_N    = 1
GP_SCK   = 10  # output
GP_MOSI  = 11  # output
GP_MISO  = 12  # input
GP_CS    = 13  # output

# init SPI
spi = SPI(SPI_N, baudrate=SPEED_HZ, polarity=0, phase=0, bits=8,
          sck=Pin(GP_SCK), mosi=Pin(GP_MOSI), miso=Pin(GP_MISO))

# chip select idles high when bus inactive
spi_cs = Pin(GP_CS, Pin.OUT)
spi_cs.high()  # deselected

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

def init_card() -> int or None:  # CARD_VERSION | UNKNOWN
    R1_IDLE_STATE       = 1<<0
    R1_ILLEGAL_COMMAND  = 1<<2
    RETRY_TIMES         = 100
    # cmd, arg, crc, [final_ff=0], [release=True]
    CMD_INIT            = (0, 0, 0x95)
    CMD_GET_CARD_VER    = (8, 0x01aa, 0x87, 4)

    def cmd(cmd:int, arg:int, crc:int, final_ff:int=0, release:bool=True) -> int or None:
        """Create and send a command"""
        spi_cs.low()

        txbuf = bytearray(6)
        txbuf[0] = 0x40 | cmd
        txbuf[1] = arg >> 24
        txbuf[2] = arg >> 16
        txbuf[3] = arg >> 8
        txbuf[4] = arg
        txbuf[5] = crc
        spi.write(txbuf)

        # busy-wait for response bit7==0
        rxbuf = bytearray(1)
        for _ in range(RETRY_TIMES):
            spi.readinto(rxbuf, 0xFF)
            response = rxbuf[0]
            if not (response & 0x80):
                for _ in range(final_ff):  #TODO: spi.read(final_ff, 0xFF)
                    spi.read(1, 0xFF)
                if release:
                    spi_cs.high()
                    spi.read(1, 0xFF)
                return response

        # timeout
        spi_cs.high()
        spi.read(1, 0xFF)
        return None  # NO_RESPONSE

    # clock card at least 100 cycles with cs high
    for _ in range(16):  #TODO: spi.read(16, 0xFF)
        spi.read(1, 0xFF)

    # CMD0: init card; should return R1_IDLE_STATE (allow 5 attempts)
    for _ in range(5):
        if cmd(*CMD_INIT) == R1_IDLE_STATE:
            break
    else:
        return None  # NO SDCARD

    # CMD8: determine card version
    r = cmd(*CMD_GET_CARD_VER)
    if r == R1_IDLE_STATE:
        return 2  # V2 CARD
    elif r == R1_IDLE_STATE | R1_ILLEGAL_COMMAND:
        return 1  # V1 CARD
    else:
        return 0xFF  # UNKNOWN SD CARD VER

def test():
    """Use this to test the sdcard responds"""
    card_version = init_card()
    if card_version is None: print("FAIL: card did not respond")
    else:                    print("PASS: card version:", card_version)

print("test_sd_spi program:")
print("  test_pin(10)  - toggle-test a GP pin, any number allowed")
print("  PINS: sck:10  mosi:11  miso:12  cs:13")
print("  test()        - check if sdcard responds to read-version command")

