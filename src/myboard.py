# myboard.py  16/02/2023  D.J.Whale - board defs for pins, etc

import platdeps

if platdeps.PLATFORM == platdeps.MPY:
    # picosat board GPIO numbers (not pin numbers) Raspberry Pi Pico
    RADIO_G0_GPN    = 0   # {GP0}/TX0/SDA0/DIO/PWM0A
    RADIO_CS_GPN    = 1   # {GP1}/RX0/SCL0/CS0/PWM0B
    RADIO_SCK_GPN   = 2   # GP2/SDA1/{SCK0}/PWM1A
    RADIO_MOSI_GPN  = 3   # GP3/SCL1/DO0/PWM1B
    RADIO_MISO_GPN  = 4   # GP4/TX1/SDA0/{DI0}/PWM2A
    CAMERA_CS_GPN   = 5   # {GP5}/RX1/SCL0/CS0/PWM2B
    RADIO_RES_GPN   = 6   # {GP6}/SDA1/SCK0/PWM3A
    RADIO_EN_GPN    = 7   # {GP7}/SCL1/DO0/PWM3B
    CAMERA_SDA_GPN  = 8   # GP8/TX1/{SDA0}/DI1/PWM4A
    CAMERA_SCL_GPN  = 9   # GP9/RS1/{SCL0}/CS1/PWM4B
    SDCARD_SCK_GPN  = 10  # GP10/SDA1/{SCK1}/PWM5A
    SDCARD_MOSI_GPN = 11  # GP11/SCL1/{D01}/PWM5B
    SDCARD_MISO_GPN = 12  # GP12/TX0/SDA0/{DI1}/PWM6A
    SDCARD_CS_GPN   = 13  # {GP13}/RX0/SCL0/CS1/PWM6B
    SPI1_CS_GPN     = 14  # {GP14}/SDA1/SCK1/PWM7A
    SPI0_CS_GPN     = 15  # {GP15}/PWM7B
    MISC16_GPN      = 16  # GP16/{TX0}/SDA0/DI0/PWM0A
    BUTTON_GPN      = 17  # GP17/{RX0}/SCL0/CS0/PWM0B
    I2C1_SDA_GPN    = 18  # GP18/{SDA1}/SCK0/PWM1A
    I2C1_SCL_GPN    = 19  # GP19/{SCL1}/DO0/PWM1B
    LED1_GPN        = 20  # {GP20}/TX1/SDA0/DI0/PWM2A
    LED2_GPN        = 21  # {GP21}/RX1/SCL0/CS0/PWM2B
    MISC22_GPN      = 22  # {GP22}/SDA1/SCK0/PWM3A
    #23..25 not used on Pico
    MISC26_GPN      = 26  # {GP23}/A0/SDA1/SCK1/PWM5A
    MISC27_GPN      = 27  # {GP24}/A1/SCL1/DO1/PWM5B
    MISC28_GPN      = 28  # {GP25}/A2/DI1/PWM6A

    from machine import Pin

    # General pins
    OPTION_GPN = MISC16_GPN
    option_pin = Pin(OPTION_GPN, Pin.IN)
    OPTION     = option_pin()  # read the option pin once
    # In test_radio we use OPTION=0 for receive(), OPTION=1 for send()
    # For ftag Uart tests, we show option, but don't do anything with it

    RX_LED_GPN = LED2_GPN
    rx_led_pin = Pin(RX_LED_GPN, Pin.OUT)

    class UartCfg:
        # UartLink
        BAUD_RATE  = 115_200
        PORT       = 1
        TX_GPN     = LED1_GPN  # on our test board only
        RX_GPN     = LED2_GPN  # on our test board only
        BLOCK_SIZE = 50
        # tx_pin
        # rx_pin

    class RadioCfg:
        # SPI_MODES: 0=CPOL0 CPHA0, 1=CPOL0 CPHA1 2=CPOL1 CPHA0, 3=CPOL1 CPHA1
        SPEED_HZ    = 1_000_000  # RFM69 datasheet says 10MHz max allowed
        SPI_N       = 0
        GPN_G0      = RADIO_G0_GPN  # DIO0 INT pin
        GPN_CS      = RADIO_CS_GPN
        GPN_SCK     = RADIO_SCK_GPN
        GPN_MOSI    = RADIO_MOSI_GPN
        GPN_MISO    = RADIO_MISO_GPN
        GPN_RES     = RADIO_RES_GPN  # must be low in normal operation (floats high)
        GPN_EN      = RADIO_EN_GPN  # must be high to enable regulator (floats high)
        GPN_TX_LED  = LED1_GPN
        GPN_RX_LED  = LED2_GPN
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

    class SDCardCfg:
        SPEED_SLOW_HZ = 100_000
        SPEED_FAST_HZ = 1_000_000
        SPN           = 1
        CS_GPN        = SDCARD_CS_GPN
        SCK_GPN       = SDCARD_SCK_GPN
        MOSI_GPN      = SDCARD_MOSI_GPN
        MISO_GPN      = SDCARD_MISO_GPN

else:
    pass # no defs for CPYTHON

#END: myboard.py
