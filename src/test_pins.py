# test_pins.py  23/02/2023  D.J.Whale - test arbitrary GP pins

from machine import Pin
from utime import sleep_ms

def flash(gp_no, name:str="", times:int=4, delay_ms:int=250):
    p = Pin(gp_no, Pin.OUT)
    try:
        for t in range(times):
            print("%s ON(%d)" % (name, gp_no))
            p.on()
            sleep_ms(delay_ms)
            print("%s OFF(%d)" % (name, gp_no))
            p.off()
            sleep_ms(delay_ms)
    finally:
        p = Pin(gp_no, Pin.IN)


#TODO input pins need a different test, as do analogs
#where there are multiple modes, must ask user for mode of test
#TODO: def test_di_pin(pin_no: int, name:str=None)
#TODO: def test_ai_pin(pin_no: int, name:str=None)

INPUT  = 1<<0
OUTPUT = 1<<2
ANALOG = 1<<2

#NOTE: if you fill in the adjacent pins, it will prompt the user to make sure
#that these adjacent pins are not affected when a specific pin is flashed

PIN_TABLE = (                                   #TODO vvv fill these in
    # NAME              MODE(S)                     ADJACENT     number
    ("RADIO_G0",        OUTPUT,                     "0-adj"),    # 0
    ("RADIO_CS",        OUTPUT,                     "1-adj"),    # 1
    ("RADIO_SCK",       OUTPUT,                     "2-adj"),    # 2
    ("RADIO_MOSI",      OUTPUT,                     "3-adj"),    # 3
    ("RADIO_MISO",      INPUT,                      "4-adj"),    # 4
    ("CAMERA_CS",       OUTPUT,                     "5-adj"),    # 5
    ("RADIO_RES",       OUTPUT,                     "6-adj"),    # 6
    ("RADIO_EN",        OUTPUT,                     "7-adj"),    # 7
    ("CAMERA_SDA",      INPUT | OUTPUT,             "8-adj"),    # 8
    ("CAMERA_SCL",      OUTPUT,                     "9-adj"),    # 9
    ("SDCARD_SCK",      OUTPUT,                     "10-adj"),   # 10
    ("SDCARD_MOSI",     OUTPUT,                     "11-adj"),   # 11
    ("SDCARD_MISO",     INPUT,                      "12-adj"),   # 12
    ("SDCARD_CS",       OUTPUT,                     "13-adj"),   # 13
    ("SPI1_CS",         OUTPUT,                     "14-adj"),   # 14
    ("SPI0_CS",         OUTPUT,                     "15-adj"),   # 15
    ("MISC16",          INPUT | OUTPUT,             "16-adj"),   # 16
    ("BUTTON",          INPUT,                      "17-adj"),   # 17
    ("I2C1_SDA",        INPUT | OUTPUT,             "18-adj"),   # 18
    ("I2C1_SCL",        OUTPUT,                     "19-adj"),   # 19
    ("LED1",            OUTPUT,                     "20-adj"),   # 20
    ("LED2",            OUTPUT,                     "21-adj"),   # 21
    ("MISC22",          INPUT | OUTPUT,             "22-adj"),   # 22
    None,                                                        # 23 UNUSED
    None,                                                        # 24 UNUSED
    None,                                                        # 25 UNUSED
    ("MISC26",          INPUT | ANALOG | OUTPUT,    "26-adj"),   # 26
    ("MISC27",          INPUT | ANALOG | OUTPUT,    "27-adj"),   # 27
    ("MISC28",          INPUT | ANALOG | OUTPUT,    "28-adj"),   # 28
)

NAME = 0
MODE = 1
ADJACENT = 2

def test():
    gp_no = 20  # default is first LED
    try:
        while True:
            rsp = input("GP number, or return to test(%d)?" % gp_no)
            if rsp != "":
                # change the gp_no
                try:
                    gp_no = int(rsp)
                except ValueError:
                    print("must enter a number")
                    continue

                if gp_no < 0 or gp_no >= len(PIN_TABLE) or PIN_TABLE[gp_no] is None:
                    print("Invalid pin number")
                    continue
            # else: leave the gp_no unchanged, run test again

            print("adjacent:", PIN_TABLE[gp_no][ADJACENT])
            flash(gp_no, name=PIN_TABLE[gp_no][NAME])

    except KeyboardInterrupt:
        print("\nCTRL-C")  # finished

def list():
    for i in range(len(PIN_TABLE)):
        p = PIN_TABLE[i]
        if p is not None:
            print(p[0], "GP%d" % i )  # name, gp_no

print("test_pins program:")
print("  list()        - list available pin map")
print("  flash(4)      - flash GP4 a few times")
print("  test()        - test all pins interactively")
