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

def test():
    led1 = Pin(LED1_GPN, Pin.OUT)
    led2 = Pin(LED2_GPN, Pin.OUT)

    print("LED1(20) ON")
    led1.on()
    sleep_ms(500)

    print("LED1(20) FF")
    led1.off()
    sleep_ms(500)

    print("LED2(21) ON")
    led2.on()
    sleep_ms(500)

    print("LED2(21) FF")
    led2.off()
    sleep_ms(500)


print("test_leds program:")
print("test() - test that both LEDs work")