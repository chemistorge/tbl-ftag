# test_leds.py  23/02/2023  D.J.Whale - test the two board LEDs

from machine import Pin
from utime import sleep_ms

LED1_GPN = 20  # {GP20}/TX1/SDA0/DI0/PWM2A
LED2_GPN = 21  # {GP21}/RX1/SCL0/CS0/PWM2B

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

def flash(pin, name:str="", times:int=4, delay_ms:int=250):
    for t in range(times):
        print("%s ON" % name)
        pin.on()
        sleep_ms(delay_ms)
        print("%s OFF" % name)
        pin.off()
        sleep_ms(delay_ms)

def test():
    led1 = Pin(LED1_GPN, Pin.OUT)
    led2 = Pin(LED2_GPN, Pin.OUT)

    flash(led1, "LED1(%d)" % LED1_GPN)
    flash(led2, "LED2(%d)" % LED2_GPN)

print("test_leds program:")
print("test() - test that both LEDs work")