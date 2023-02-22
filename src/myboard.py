# myboard.py  16/02/2023  D.J.Whale - board defs for pins, etc

import platdeps

if platdeps.PLATFORM == platdeps.MPY:
    from machine import Pin

    # General pins
    OPTION_GPN = 16
    option_pin = Pin(OPTION_GPN, Pin.IN)
    OPTION     = option_pin()  # read the option pin once
    # In test_radio we use OPTION=0 for receive(), OPTION=1 for send()
    # For ftag Uart tests, we show option, but don't do anything with it

    RX_LED_GPN = 27
    rx_led_pin = Pin(RX_LED_GPN, Pin.OUT)

    class UartCfg:
        # UartLink
        BAUD_RATE  = 115_200
        PORT       = 1
        TX_GPN     = 20  # LED1 on picosat
        RX_GPN     = 21  # LED2 on picosat
        BLOCK_SIZE = 50
        # tx_pin
        # rx_pin

    class RadioCfg:
        # SPI_MODES: 0=CPOL0 CPHA0, 1=CPOL0 CPHA1 2=CPOL1 CPHA0, 3=CPOL1 CPHA1
        SPEED_HZ    = 1_000_000  # RFM69 datasheet says 10MHz max allowed
        SPI_N       = 0
        GPN_G0      = 0  # DIO0 INT pin
        GPN_CS      = 1
        GPN_SCK     = 2
        GPN_MOSI    = 3
        GPN_MISO    = 4
        GPN_RES     = 6  # must be low in normal operation (floats high)
        GPN_EN      = 7  # must be high to enable regulator (floats high)
        GPN_TX_LED = 26
        GPN_RX_LED = 27
        # Don't make Pins outputs here, do in driver TODO: or set initial states here
        #g0_pin     = Pin(GPN_G0)     ##, Pin.IN)
        #cs_pin     = Pin(GPN_CS)     ##, Pin.OUT)
        #sck_pin    = Pin(GPN_SCK)    ##, Pin.OUT)
        #mosi_pin   = Pin(GPN_MOSI)   ##, Pin.OUT)
        #miso_pin   = Pin(GPN_MISO)   ##, Pin.IN)
        #res_pin    = Pin(GPN_RES)    ##, Pin.OUT)
        #en_pin     = Pin(GPN_EN)     ##, Pin.OUT)
        #tx_led_pin = Pin(GPN_TX_LED) ##, Pin.OUT)
        #rx_led_pin = Pin(GPN_RX_LED) ##, Pin.OUT)

        #TODO: parameters we might want to fiddle with later
        #TX_POWER       = 0dBm
        #BAUD_RATE      = 250_000
        #DEVIATION_FREQ = 250_000
        #CARRIER_FREQ   = 433_920_000
        #DUTY_CYCLE     = 100

else:
    pass # no defs for CPYTHON

#END: myboard.py
