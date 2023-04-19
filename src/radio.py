# radio.py  09/05/2022  D.J.Whale

import platdeps  # time_sleep_ms time_ms
import myboard

#----- PLATFORM INTEGRATION ----------------------------------------------------

# Pico, temporary until we init pins in myboard
from machine import Pin, SPI

#Note, if we set pin states in RadioCfg, just copy pins here?
#or leave all pins as inputs in RadioCfg, and turn to OUT here,
#but then we need the Pin.OUT identifier
# GPN_CS     = myboard.RadioCfg.GPN_CS  # or pin?
# SPI_N      = myboard.RadioCfg.SPI_N
# SPEED_HZ   = myboard.RadioCfg.SPEED_HZ
# GPN_SCK    = myboard.RadioCfg.GPN_SCK
# GPN_MOSI   = myboard.RadioCfg.GPN_MOSI
# GPN_RES    = myboard.RadioCfg.GPN_RES
# GPN_EN     = myboard.RadioCfg.GPN_EN
# GPN_TX_LED = myboard.RadioCfg.GPN_TX_LED
# GPN_RX_LED = myboard.RadioCfg.GPN_RX_LED
# GPN_G0     = myboard.RadioCfg.GPN_G0

class PicoSPIRadio:
    """Handle the whole bus interface to the Adafruit RFM69HCW radio board"""
    def __init__(self, cspin, link, txledpin=None, rxledpin=None, resetpin=None,
                 enpin=None, intpin=None, cspol=0, trace:bool=False):
        if not trace: self._trace = None
        else        : self._trace = print
        self._link = link
        self._resetpin = resetpin
        self._txledpin = txledpin
        self._rxledpin = rxledpin
        self._cspin    = cspin
        self._enpin    = enpin
        self._intpin   = intpin
        if enpin is not None: enpin(1)  # prevent it floating around

        if cspol:  # active high
            self.select   = lambda: self._cspin(1)
            self.deselect = lambda: self._cspin(0)
        else:  # active low
            self.select   = lambda: self._cspin(0)
            self.deselect = lambda: self._cspin(1)
        self.deselect()  # correct idle state at start

    # keep the static inspector happy
    def select(self) -> None: pass
    def deselect(self) -> None: pass

    def power(self, flag=True) -> None:
        """Supply power to the radio regulator or not"""
        if self._trace: self._trace("radio:power %s" % flag)
        if self._enpin is not None:
            self._enpin(flag)

    def is_int(self) -> bool:
        """Is the interrupt pin asserted?"""
        if self._intpin is not None:
            return self._intpin()

    def reset(self) -> None:
        """Hard reset the radio"""
        if self._trace: self._trace("radio:reset")
        if self._resetpin is not None:
            self._resetpin(1)
            platdeps.time_sleep_ms(150)
            self._resetpin(0)
            platdeps.time_sleep_ms(100) # allow a long holdoff until first reg write

    def txing(self, flag:bool) -> None:
        if self._trace: self._trace("radio:txing %s" % str(flag))

        if self._txledpin is not None:
            self._txledpin(1 if flag else 0)
        else:
            pass ##print("txled:%s" % flag)

    def rxing(self, flag:bool) -> None:
        if self._trace: self._trace("radio:rxing %s" % str(flag))
        if self._rxledpin is not None:
            self._rxledpin(1 if flag else 0)
        else:
            pass ##print("rxled:%s" % flag)

    def transfer(self, tx=None, rx=None, select:bool=True) -> None:
        if self._trace: self._trace("radio:transfer %s" % str(tx))
        #TODO: cmd() decode ^^^

        if select: self.select()

        if isinstance(tx, int):
            # tx fixed value, with receive up to length rxbuf
            assert rx is not None
            self._link.readinto(rx, tx)

        elif tx is not None:
            if rx is None:
                # tx only of length txbuf
                self._link.write(tx)
            else:
                # tx and rx lengths must be same, bufs same or diff
                ##print("write %s read back" % hexstr(tx))
                self._link.write_readinto(tx, rx)
                ##print("got:%s" % hexstr(rx))

        else:
            # rx only, will tx 0's
            assert rx is not None
            self._link.readinto(rx, 0x00)

        if select: self.deselect()

    def byte(self, tx_byte:int) -> int:
        """Transfer a single byte"""
        if self._trace: self._trace("radio:byte %02X" % tx_byte)
        return self._link.read(1, tx_byte)[0]

def get_radio_link():
    # SPI_MODES: 0=CPOL0 CPHA0, 1=CPOL0 CPHA1 2=CPOL1 CPHA0, 3=CPOL1 CPHA1
    #TODO: DIO0 pin not yet mapped to G0 in radio init config, running polled.
    #TODO: might pass in Pin() classes from myboard
    #but must make sure that initial states in MyBoard are correct.

    return PicoSPIRadio(Pin(myboard.RadioCfg.GPN_CS, Pin.OUT),
                    SPI(myboard.RadioCfg.SPI_N,
                        baudrate = myboard.RadioCfg.SPEED_HZ,
                        polarity = 0,
                        phase    = 0,
                        bits     = 8,
                        sck      = Pin(myboard.RadioCfg.GPN_SCK),
                        mosi     = Pin(myboard.RadioCfg.GPN_MOSI),
                        miso     = Pin(myboard.RadioCfg.GPN_MISO)),
                    resetpin = Pin(myboard.RadioCfg.GPN_RES,    Pin.OUT),
                    enpin    = Pin(myboard.RadioCfg.GPN_EN,     Pin.OUT),
                    txledpin = Pin(myboard.RadioCfg.GPN_TX_LED, Pin.OUT),
                    rxledpin = Pin(myboard.RadioCfg.GPN_RX_LED, Pin.OUT),
                    intpin   = Pin(myboard.RadioCfg.GPN_G0,     Pin.IN))

def hexstr(data) -> str:
    """Print a run of bytes as a hexascii string"""
    if data is None: return ""
    res = []
    for b in data:
        res.append("%02X" % b)
    return " ".join(res)

def byte0(n:int) -> int: return n       & 0xFF
def byte1(n:int) -> int: return (n>>8)  & 0xFF
def byte2(n:int) -> int: return (n>>16) & 0xFF
def byte3(n:int) -> int: return (n>>24) & 0xFF

#----- RFM69 -------------------------------------------------------------------

class RFM69:
    """A generic RFM69 radio with no specific configuration"""
    VARIANT_HCW    = True  # aerial routing is different on high power device
    MTU            = 66
    _WRITE         = 0x80

    #----- 00-10: COMMON (v1.3 page 63 table 24)
    R_FIFO          = 0x00
    R_OPMODE        = 0x01
    V_OPMODE_STBY     = 0x04
    V_OPMODE_TX       = 0x0C
    V_OPMODE_RX       = 0x10
    R_DATAMODUL     = 0x02
    V_DATAMODUL_OOK   = 0x08  # packet mode, OOK, no shaping
    ##V_DATAMODUL_FSK   = 0x00  # packet mode, FSK, no shaping
    V_DATAMODUL_FSK   = 0b0_00_00_0_01  # packet mode, FSK, gaussian BT=1.0
    R_BITRATEMSB    = 0x03
    R_BITRATELSB    = 0x04
    R_FDEVMSB       = 0x05
    V_FDEVMSB_30      = 0x01  # frequency deviation 5kHz 0x0052 -> 30kHz 0x01EC
    R_FDEVLSB       = 0x06
    V_FDEVLSB_30      = 0xEC
    R_FRMSB         = 0x07
    V_FRMSB_433_92    = 0x6C
    V_FRMSB_434_3     = 0x6C
    R_FRMID         = 0x08
    V_FRMID_433_92    = 0x7A
    V_FRMID_434_3     = 0x93
    R_FRLSB         = 0x09
    V_FRLSB_433_92    = 0xE1
    V_FRLSB_434_3     = 0x33
    R_OSC1          = 0x0A
    R_AFCCTRL       = 0x0B
    V_AFCCTRLS        = 0x00  # standard AFC routine
    V_AFCCTRLI        = 0x20  # improved AFC routine
    # RESERVED 0C
    R_LISTEN1       = 0x0D
    R_LISTEN2       = 0x0E
    R_LISTEN3       = 0x0F
    R_VERSION       = 0x10
    V_VERSION         = 0x24
    #----- 11-13: TRANSMITTER (v1.3 page 66 table 25)
    R_PALEVEL       = 0x11
    R_PARAMP        = 0x12
    R_OCP           = 0x13
    #----- 14-24: RECEIVER (v1.3 page 67 table 26)
    # RESERVED 14,15,16,17
    R_LNA           = 0x18
    V_LNA_50          = 0x08  # LNA input impedance 50 ohms
    V_LNA_50G         = 0x0E  # LNA input impedance 50 ohms, LNA gain -> 48db
    V_LNA_200         = 0x88  # LNA input impedance 200 ohms
    R_RXBW          = 0x19
    V_RXBW_60         = 0b_010_00_011    ##0x43  # cutoff-dcofs-cancel(010) bw-mant(00) bw-exp(011)
    V_RXBW_120        = 0b_010_00_001    ##0x41  # cutoff-dcofs-cancel(010) bw-mant(00) bw-exp(001)
    V_RXBW_AFL        = 0b_111_00_000    #TESTING: adafruit value
    R_AFCBW         = 0x1A
    V_AFCBW_AFL     = 0b_111_00_000      #TESTING: adafruit value
    R_OOKPEAK       = 0x1B
    R_OOKAVG        = 0x1C
    R_OOKFIX        = 0x1D
    R_AFCFEI        = 0x1E
    R_AFCMSB        = 0x1F
    R_AFCLSB        = 0x20
    R_FE1MSB        = 0x21
    R_FEILSB        = 0x22
    R_RSSICONFIG    = 0x23
    M_RSSIDONE        = 0x02
    M_RSSISTART       = 0x01
    R_RSSIVALUE     = 0x24
    #----- 25-2B: IRQ AND PIN (v1.3 page 69 table 27)
    R_DIOMAPPING1   = 0x25
    R_DIOMAPPING2   = 0x26
    R_IRQFLAGS1     = 0x27
    M_MODEREADY       = 0x80
    M_RXREADY         = 0x40
    M_TXREADY         = 0x20
    M_PLLLOCK         = 0x10
    M_RSSI            = 0x08
    M_TIMEOUT         = 0x04
    M_AUTOMODE        = 0x02
    M_SYNCADDRMATCH   = 0x01
    R_IRQFLAGS2     = 0x28
    M_FIFOFULL        = 0x80
    M_FIFONOTEMPTY    = 0x40
    M_FIFOLEVEL       = 0x20
    M_FIFOOVERRUN     = 0x10
    M_PACKETSENT      = 0x08
    M_PAYLOADREADY    = 0x04
    M_CRCOK           = 0x02
    R_RSSITHRESH    = 0x29
    V_RSSITHRESH_220  = 0xDC  # RSSI threshold 0xE4 -> 0xDC
    R_RXTIMEOUT1    = 0x2A
    R_RXTIMEOUT2    = 0x2B
    #----- 2C-4D: PACKET ENGINE (v1.3 page 71 table 28)
    R_PREAMBLEMSB   = 0x2C
    R_PREAMBLELSB   = 0x2D
    V_PREAMBLELSB_3   = 0x03  # preamble size LSB 3
    V_PREAMBLELSB_5   = 0x05  # preamble size LSB 5
    R_SYNCCONFIG    = 0x2E
    V_SYNCCONFIG0     = 0x00  # 0 bytes of tx sync
    V_SYNCCONFIG1     = 0x80  # 1 byte  of tx sync
    V_SYNCCONFIG2     = 0x88  # 2 bytes of tx sync
    V_SYNCCONFIG3     = 0x90  # 3 bytes of tx sync
    V_SYNCCONFIG4     = 0x98  # 4 bytes of tx sync
    R_SYNCVALUE1    = 0x2F
    R_SYNCVALUE2    = 0x30
    R_SYNCVALUE3    = 0x31
    R_SYNCVALUE4    = 0x32
    R_SYNCVALUE5    = 0x33
    R_SYNCVALUE6    = 0x34
    R_SYNCVALUE7    = 0x35
    R_SYNCVALUE8    = 0x36
    R_PACKETCONFIG1 = 0x37
    R_PAYLOADLEN    = 0x38
    R_NODEADRS      = 0x39
    R_BROADCASTADRS = 0x3A
    R_AUTOMODES     = 0x3B
    R_FIFOTHRESH    = 0x3C
    V_FIFOTHRESH_1    = 0x81  # start packet tx on: at least one byte in FIFO
    V_FIFOTHRESH_30   = 0x1E  # start pcacket tx on: wait for 30 bytes in FIFO
    R_PACKETCONFIG2 = 0x3D
    R_AESKEY1       = 0x3E
    # AESKEY2..AESKEY16 = 3F..4D
    #----- 4E-57: TEMPERATURE (v1.3 page 74 table 29)
    R_TEMP1         = 0x4E
    R_TEMP2         = 0x4F
    # RESERVED 50..57
    #----- 58-7F: TEST (v1.3 page 74 table 30)
    R_TESTLNA       = 0x58
    # RESERVED 59
    R_TESTPA1       = 0x5A
    # RESERVED 5B
    R_TESTPA2       = 0x5C
    # RESERVED 5D..6E
    R_TESTDAGC     = 0x6F
    # RESERVED 70
    R_TESTAFC      = 0x71
    # RESERVED 72..7F

    FXOSC    = 32_000_000  # datasheet v1.3 page 12  Table 5
    FSTEP_HZ = 61          # datasheet v1.3 page 13  Table 5
    #NOTE, this is *really* FXOSC / 524_288 = 61.03515625 Hz

    # datasheet v1.3 page 64 Table 24
    @staticmethod
    def fdev_word_for(fstep_hz:int, fdev_hz:int):
        fdev_word = int(fdev_hz / fstep_hz)
        ##print("fdev %dHz -> word:%04X" % (fdev_hz, fdev_word))
        return fdev_word

    # datasheet v1.3 page 19
    @staticmethod
    def baud_word_for(fosc:int, rate:int) -> int:
        brw = int(fosc / rate) + 1  # worst case
        ##print("baud rate word:%04X" % brw)
        assert brw < 0x10000, "brw overflow, max:0xFFFF got:0x%08X" % brw
        return brw

    RX_POLL = 0
    RX_INT  = 1

    def __init__(self, link=None):
        self._spi = link
        self._mode = self.V_OPMODE_STBY
        self._rxmode = self.RX_POLL
        self._regbuf = bytearray(2)  # reusable buffer for reg reads and writes
        self._rssi   = None  # no value stored

    def readreg(self, addr: int) -> int:
        self._regbuf[0] = addr
        self._regbuf[1] = 0
        self._spi.transfer(self._regbuf, self._regbuf)
        return self._regbuf[1]

    def writereg(self, addr: int, value: int) -> None:
        ##print("writereg:%02X=%02X" % (addr, value))
        self._spi.transfer(bytearray((addr | self._WRITE, value)))

    ##def checkreg(self, addr: int, mask: int, value: int) -> bool:
    ##    v = self.readreg(addr)
    ##    return (v & mask) == value

    def waitreg(self, addr: int, mask: int, value: int):
        ##print("waitreg: %02X & %02X == %02X?" % (addr, mask, value))
        while True:
            v = self.readreg(addr)
            ##print("  got:%02X" % v, end=" ")
            if (v & mask) == value:
                ##print("YES")
                return
            else:
                ##print("NO")
                ##platdeps.time_sleep_ms(100)
                pass

    def writefifo(self, buf) -> None:
        """Send all bytes to the FIFO buffer"""
        #NOTE: irqflags comes back in the read buffer if we want it
        self._spi.select()
        self._spi.byte(self.R_FIFO | self._WRITE)
        self._spi.transfer(buf, select=False)
        self._spi.deselect()

    def clearfifo(self) -> None:
        while (self.readreg(self.R_IRQFLAGS2) & self.M_FIFONOTEMPTY) == self.M_FIFONOTEMPTY:
            self.readreg(self.R_FIFO)

    def reset(self) -> None:
        self._spi.txing(False)
        self._spi.rxing(False)
        self._spi.reset()

    def setmode(self, mode: int) -> None:
        self._spi.txing(False)
        self._spi.rxing(False)

        self.writereg(self.R_OPMODE, mode)

        if mode == self.V_OPMODE_TX:
            self.wait_tx_ready()
            self._spi.txing(True)

        elif mode == self.V_OPMODE_RX:
            self.wait_ready()
            self.writereg(self.R_RSSICONFIG, self.M_RSSISTART)
            self._spi.rxing(True)

        else: # e.g. STBY
            self.wait_ready()

        self._mode = mode

    def getmode(self):
        return self._mode

    def wait_ready(self) -> None:
        self.waitreg(self.R_IRQFLAGS1, self.M_MODEREADY, self.M_MODEREADY)

    def wait_tx_ready(self) -> None:
        FLAGS = self.M_MODEREADY | self.M_TXREADY
        self.waitreg(self.R_IRQFLAGS1, FLAGS, FLAGS)

    def transmit(self, payload:bytes, times:int=1) -> None:
        # Note, when PA starts up, radio inserts a 01 at start before any user data
        # we might need to pad away from this by sending a sync of many zero bits
        # to prevent it being misinterpreted as a preamble, and prevent it causing
        # the first bit of the preamble being twice the length it should be in the
        # first packet.

        # CHECK
        pllen = len(payload)
        assert times >= 1 and 1 <= pllen <= self.MTU

        # CONFIGURE
        # Start transmitting when a full payload is loaded. So for '15':
        # level triggers when it 'strictly exceeds' level (i.e. 16 bytes starts tx,
        # and <=15 bytes triggers fifolevel irqflag to be cleared)
        # We already know from earlier that payloadlen<=32 (which fits into half a FIFO)
        self.writereg(self.R_FIFOTHRESH, pllen - 1)

        # TRANSMIT: Transmit a number of payloads back to back
        for i in range(times):
            self.writefifo(payload)
            # Tx will auto start when fifolevel is exceeded by loading the payload
            # so the level register must be correct for the size of the payload
            # otherwise transmit will never start.
            # wait for FIFO to not exceed threshold level
            self.waitreg(self.R_IRQFLAGS2, self.M_FIFOLEVEL, 0)

        # WAIT: wait for FIFO empty, to indicate transmission completed
        self.waitreg(self.R_IRQFLAGS2, self.M_FIFONOTEMPTY, 0)

        # CONFIRM: Was the transmit ok, in case of overruns etc
        ##uint8_t irqflags1 = HRF_readreg(HRF_ADDR_IRQFLAGS1)
        ##uint8_t irqflags2 = HRF_readreg(HRF_ADDR_IRQFLAGS2)
        ##if (((irqflags2 & HRF_MASK_FIFONOTEMPTY) != 0) || ((irqflags2 & HRF_MASK_FIFOOVERRUN) != 0))
        ##{
        ##    error("FIFO not empty or overrun at end of burst")
        ##}

    def recv_rdy(self) -> bool:
        """Is there something to be received?"""
        if self._rxmode == self.RX_INT:
            return self._spi.is_int()
        else:  # self.RX_POLL:
            irqflags2 = self.readreg(self.R_IRQFLAGS2)
            return (irqflags2 & self.M_PAYLOADREADY) == self.M_PAYLOADREADY

    def readfifo_cbp_into(self, rxbuf) -> int:
        """Receive a count byte preceeded block of data"""
        #NOTE: only call this if you know there is something in the FIFO
        # clear buffer first, for diags
        for i in range(len(rxbuf)):
            rxbuf[i] = 0

        self._spi.select()
        self._spi.byte(self.R_FIFO)  #  prime the burst receiver

        length = self._spi.byte(self.R_FIFO)  # read the length byte
        if length > len(rxbuf):
            self._spi.deselect()
            print("warning: rxbuf too small, want:%d got:%d" % (length+1, len(rxbuf)))
            self.clearfifo()
            return 0  # NOTDONE

        #SLOW RECEIVE FIFO data
        rxbuf[0] = length
        for i in range(length):
            b = self._spi.byte(self.R_FIFO)
            rxbuf[i+1] = b
        self._spi.deselect()

        # read RSSI value, if flag says it has been acquired
        rssi_rdy = (self.readreg(self.R_RSSICONFIG) & self.M_RSSIDONE) != 0
        if rssi_rdy:
            ##print("<<RSSIRDY=1")  # TESTING
            self._rssi = -self.readreg(self.R_RSSIVALUE) / 2
        else:
            ##print("<< NO RSSI AVAILABLE?")  # TESTING
            self._rssi = None

        # set the flag again for next rx packet
        self.writereg(self.R_RSSICONFIG, self.M_RSSISTART)

        return length+1  # DONE, actual nbytes in buffer including cbp

        #FAST RECEIVE (NOTE:not working on Pico, suspect lack of spi(write=) param
        # rxbuf[0] = length  # user sees the CBP also
        # print("delay for packet")
        # platdeps.time_sleep_ms(250)  # wait for rest of payload to fill buffer
        # self._spi.transfer(self.R_FIFO, memoryview(rxbuf[1:length]), select=False)
        # self._spi.deselect()
        # print("packet apparently received")
        # return length+1  # DONE, actual length

    def get_rssi(self) -> float or None: # in dBm in 0.5dB steps
        """RSSI of last received packet, in dBm, in 0.5dBm steps"""
        return self._rssi  # will be None if not yet acquired

#----- RADIO -------------------------------------------------------------------

class RadioISM:
    """A specific configuration of the RFM69 radio, for data transfer over FSK"""
    class RadioError(Exception): pass

    #TODO: preamble length
    SYNCWORD  = 0x2DD4  # same as energenie, and RadioHead/adafruit
    # see also swra048 table 9 for channel bandwidth limits at higher tx power
    BAUD_RATE = 250_000  # datasheet v1.3 sec 3.3.2 table 9 (FSK 1.2kbps..300kbps)
    FDEV_HZ   = 250_000

    R = RFM69
    BAUD_WORD = R.baud_word_for(R.FXOSC, BAUD_RATE)
    FDEV_WORD = R.fdev_word_for(R.FSTEP_HZ, FDEV_HZ)
    MTU       = R.MTU

    # see: https://www.ti.com/lit/an/swra048/swra048.pdf table 9
    # see datasheet table 10
    #R_PALEVEL            012 xxxxx
    # normal power radio, tx on RFIO pin (-18dBm..+13dBm)
    V_RFIO_N18_DBM   = 0b_100_00000    # PA0: -18dBm+0 = -18dBm
    V_RFIO_10_DBM    = 0b_100_11100    # PA0: -18dBm+28 = 10dBm (swra048 limit in UK)
    ##V_RFIO_MAX     = 0b_100_11111    # PA0: -18dBm+31 = 13dBm (DON'T USE IN UK)

    # high power (HCW) radio, tx on PA_BOOST pin  (PA1:-2dBm..13dBm, PA1+2:+2dBm..+17dBm, PA1+2+HIGHP:+5dBm..+20dBm)
    # datasheet: only the 16 upper values of PLEV are used with PA1 or PA2 combinations
    V_PABOOST_0_DBM  = 0b_010_1_0010    # PA1: -18dBm + PLEV(18) = 0dBm   # swra048 433.05..434.79 0dBm duty(any) chbw(any)
    V_PABOOST_10_DBM = 0b_010_1_1100    # PA1: -18dBm + PLEV(28) = 10dBm  # swra048 433.05..434.79 10dBm duty(<10%) or chbw(<25kHz)

    FSK_CFG = (
        #----- 00-10: COMMON (v1.3 page 63 table 24)
        # R_FIFO            def: 00
        # R_OPMODE          def: 0000 0100
        (R.R_DATAMODUL,     R.V_DATAMODUL_FSK),
        (R.R_BITRATEMSB,    byte1(BAUD_WORD)),  # baud rate
        (R.R_BITRATELSB,    byte0(BAUD_WORD)),  # ...
        (R.R_FDEVMSB, byte1(FDEV_WORD)),        # frequency deviation
        (R.R_FDEVLSB, byte0(FDEV_WORD)),        # ...
        (R.R_FRMSB,         R.V_FRMSB_434_3),   # carrier freq
        (R.R_FRMID,         R.V_FRMID_434_3),   # ...
        (R.R_FRLSB,         R.V_FRLSB_434_3),   # ...
        # R_OSC1            def: 0 1 000001
        (R.R_AFCCTRL,       R.V_AFCCTRLS),      # standard AFC routine
        # R_LISTEN1         def: 10 01 0 01 0
        # R_LISTEN2         def: F5
        # R_LISTEN3         def: 20
        #----- 11-13: TRANSMITTER (v1.3 page 66 table 25)
        (R.R_PALEVEL,       V_PABOOST_0_DBM),   # (any duty cycle, any channel bandwidth at 0dBm)
        ##R_PARAMP          def: 0000 1001      # 40uS
        ##(R.R_OCP,           0x00),            # RFM69HCW over current protect off (only for 20dBm mode)
        #----- 14-24: RECEIVER (v1.3 page 67 table 26)
        (R.R_LNA,           R.V_LNA_50),        # 200ohms, gain by AGC loop -> 50ohms
        (R.R_RXBW,          R.V_RXBW_AFL),      #TESTING: adafruit value
        #R_AFCBW            def: 100 01 011
        (R.R_AFCBW,         R.V_AFCBW_AFL),     #TESTING: adafruit value
        #R_OOKPEAK          def: 01 000 000
        #R_OOKAVG           def: 10 000000
        #R_OOKFIX           def: 0000 0110
        #R_AFCFEI           def: 0 0 0 1 0 0 0 0
        #R_AFCMSB           def: 00
        #R_AFCLSB           def: 00
        #R_FEIMSB           def: -
        #R_FEILSB           def: -
        #R_RSSICONFIG       def: 000000 1 0
        #R_RSSIVALUE        def: FF
        #----- 25-2B: IRQ AND PIN (v1.3 page 69 table 27)
        #R_DIOMAPPING1      def: 00 00 00 00
        #R_DIOMAPPING2      def: 00 00 0 111
        #R_IRQFLAGS1        def: 1 0 0 0 0 0 0 0
        #R_IRQFLAGS2        def: 0 0 0 0 0 0 0 0
        #R_RSSITHRESH       def: E4
        #R_RXTIMEOUT1       def: 00
        #R_RXTIMEOUT2       def: 00
        #----- 2C-4D: PACKET ENGINE (v1.3 page 71 table 28)
        #R_PREAMBLEMSB      def: 00
        (R.R_PREAMBLELSB,   R.V_PREAMBLELSB_5),     # extended, to see if we can improve RSSI detection
        (R.R_SYNCCONFIG,    R.V_SYNCCONFIG2),       # Size of the Sync word
        (R.R_SYNCVALUE1,    byte1(SYNCWORD)),
        (R.R_SYNCVALUE2,    byte0(SYNCWORD)),
        #R_SYNCVALUE3       def: 01
        #R_SYNCVALUE4       def: 01
        #R_SYNCVALUE5       def: 01
        #R_SYNCVALUE6       def: 01
        #R_SYNCVALUE7       def: 01
        #R_SYNCVALUE8       def: 01
        ##(R.R_PACKETCONFIG1, 0b1_01_0_0_00_0),     # Variable length, Manchester coding
        (R.R_PACKETCONFIG1,   0b1_10_0_0_00_0),     # Variable length, Whitening coding
        (R.R_PAYLOADLEN,    MTU),                   # max Length in RX, not used in Tx
        #R_NODEADRS         def: 00
        #R_BROADCASTADRS    def: 00
        #R_AUTOMODES        def: 000 000 00
        #R_FIFOTHRESH       def: 1 0001111
        #R_PACKETCONFIG2    def: 0000 0 0 1 0       # AutoRxRestartOn
        #R_AESKEY1..16      def: 00
        #----- 4E-57: TEMPERATURE (v1.3 page 74 table 29)
        #R_TEMP1            def: 0000 0 0 01
        #R_TEMP2            def: --
        #----- 58-7F: TEST (v1.3 page 74 table 30)
        #R_TESTLNA          def: 1B
        #R_TESTPA1          def: 55
        #R_TESTPA2          def: 70
        #R_TESTDAGC         def: 30
        #R_TESTAFC          def: 00
    )

    CFGS = (FSK_CFG, )
    FSK       = 0
    # TODO: change to None, as 0xFFFFFFFF might overflow on some platforms
    FOREVER   = 0xFFFFFFFF

    def __init__(self, link=None):
        if link is None:
            link = get_radio_link()
        self._rfm = RFM69(link)
        self._configured = False
        self._is_on = False
        self._mode = self._rfm.V_OPMODE_STBY
        self._cfg = None
        self._rxbuf = bytearray(self.MTU)

    def get_version(self) -> int:
        return self._rfm.readreg(RFM69.R_VERSION)

    def get_rssi(self) -> float or None: # in dBm in 0.5dB steps
        """RSSI of last received packet, in dBm, in 0.5dBm steps"""
        return self._rfm.get_rssi()  # will be None if not yet acquired

    def loadtable(self, table:tuple) -> None:
        for entry in table:
            reg, value = entry
            self._rfm.writereg(reg, value)

    def want_cfg(self, cfg):
        if self._cfg != cfg:
            self._configure(self.CFGS[cfg])
            self._cfg = cfg

    def _configure(self, cfg):
        rv = self.get_version()
        if rv != RFM69.V_VERSION:
            raise self.RadioError("Unexpected radio version, want:%d got:%d" % (RFM69.V_VERSION, rv))
        self.loadtable(cfg)
        self._configured = True

    def is_configured(self) -> bool:
        return self._configured

    def is_on(self) -> bool:
        return self._is_on

    def on(self):
        if not self.is_configured():
            #radio EN=true
            self._rfm.reset()
            self.want_cfg(self.FSK)
        self._rfm.setmode(self._rfm.V_OPMODE_STBY)
        self._is_on = True

    def always_receive(self) -> None:
        """Leave the radio permanently in receive"""
        # This reduces the chance of missing payloads
        if not self.is_on(): self.on()
        self.want_cfg(self.FSK)  # we only support FSK receive at present
        self._rfm.setmode(self._rfm.V_OPMODE_RX)

    def send(self, buffer, info:dict or None=None, times:int=1) -> None:  #duck-typing: dttk.Buffer
        _ = info   # argused
        _ = times  # argused  - TODO: might pass in info

        entry_mode = self._rfm.getmode()
        if entry_mode != self._rfm.V_OPMODE_TX:
            self._rfm.setmode(self._rfm.V_OPMODE_TX)

        # Buffer
        buffer.read_with(self._rfm.transmit)

        # bytes, bytearray, memoryview
        ##self._rfm.transmit(buffer, times)

        if self._rfm.getmode() != entry_mode:
            self._rfm.setmode(entry_mode)

    def recvinto(self, buffer, info: dict or None=None, wait:int=0) -> int or None:
        """Try to receive a single packet"""

        _ = info  # argused

        # if radio not in receive, put it into receive
        entry_mode = self._rfm.getmode()
        if entry_mode != self._rfm.V_OPMODE_RX:
            self._rfm.setmode(self._rfm.V_OPMODE_RX)

        # wait for timeout time to receive a packet
        ends_at = platdeps.time_ms() + wait
        nb = 0  # NODATA by default
        while True:
            if self._rfm.recv_rdy():
                # Buffer
                nb = buffer.write_with(self._rfm.readfifo_cbp_into)

                # bytes, bytearray, memoryview
                ##nb = self._rfm.readfifo_cbp_into(buffer[:])
                if nb is None or nb > 0: break  # EOF or DATA
            #NODATA
            if platdeps.time_ms() > ends_at: break  # NODATA/TIMEOUT

        # if we changed mode, restore it back
        if self._rfm.getmode() != entry_mode:
            self._rfm.setmode(entry_mode)

        return nb  # number of bytes in buffer, including len byte

    def off(self):
        self._rfm.setmode(self._rfm.V_OPMODE_STBY)
        #radio EN=False
        self._is_on = False


#END: radio.py
