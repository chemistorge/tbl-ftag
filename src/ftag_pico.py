# ftag_pico.py  22/01/2023  D.J.Whale - pico based adaptor to file transfer agent
#NOTE: for use on PICO micropython only
# it sets the deps for the dttk module
# but in this module, it can use functions directly

import utime
import os
import uhashlib
import dttk
from machine import UART, Pin
import perf
import micropython

UART_BAUD_RATE  = 115200
UART_PORT       = 1
UART_TX_GP      = 20  # LED1 on picosat
UART_RX_GP      = 21  # LED2 on picosat
BLOCK_SIZE      = 50

@micropython.viper
def crc16_mp_v(data:ptr8, length:int) -> int:
    ##CRC16_POLY = const(0x1021)  # CCITT-16
    crcsum = 0xFFFF

    idx = 0
    while length != 0:
        # add_byte
        v = 0x80
        this_byte = data[idx]
        idx += 1
        while v != 0:
            bit = crcsum & 0x8000
            crcsum <<= 1
            if this_byte & v:  crcsum += 1
            if bit:            crcsum ^= 0x1021  #CRC16_POLY
            v >>= 1
        length -= 1

    # finish
    for i in range(16):
        bit = crcsum & 0x8000
        crcsum <<= 1
        if bit: crcsum ^= 0x1021  #CRC16_POLY
    return crcsum & 0xFFFF  #  keep within a U16

#TODO: do this with import platdeps
class MicroPythonDeps:
    time_time        = utime.time      # seconds, int
    time_perf_time   = utime.ticks_us  # us, int
    time_ms          = utime.ticks_ms  # ms, int
    time_sleep_ms    = utime.sleep_ms  # ms, int
    os_path_basename = lambda p: p     #NOTE: TEMPORARY fix
    os_rename        = os.rename
    os_unlink        = os.remove
    filesize         = lambda filename: os.stat(filename)[6]
    hashlib_sha256   = uhashlib.sha256
    message          = print
    crc16            = lambda data, length: crc16_mp_v(data[:], length)  # viper enhanced fast algorithm

    @staticmethod
    def decode_to_str(b:bytes) -> str:
        # There is no "errors='ignore'" on Pico
        try:
            return b.decode()
        # Pico throws UnicodeError, not UnicodeDecodeError
        except UnicodeError:
            print("unicode decode error")
            return "<UnicodeError>"  # this is the best we can do

dttk.set_deps(MicroPythonDeps)

class UStats:
    def __init__(self):
        ##self.data = 0
        ##self.nodata = 0
        self.rxfull = 0
        self.minbytes = None
        self.maxbytes = None
        ##self.rdsizes  = []

    def update(self, nb:int) -> None:
        ##uart_stats.data += 1
        # MINMAX for what we read in each chunk from the uart peripheral
        if uart_stats.minbytes is None:
            uart_stats.minbytes = nb
        elif nb < uart_stats.minbytes:
            uart_stats.minbytes = nb

        if uart_stats.maxbytes is None:
            uart_stats.maxbytes = nb
        elif nb > uart_stats.maxbytes:
            uart_stats.maxbytes = nb

        ## keep a list of read sizes into the buffer
        ##DISABLED uart_stats.rdsizes.append(nb)

    def __str__(self) -> str:
        return "rxfull:%d minbytes:%s maxbytes:%s" % (
            self.rxfull, str(self.minbytes), str(self.maxbytes))

uart_stats = UStats()


class UartLink(dttk.Link):
    MTU = 64  # if None, no MTU is enforced
    # measured via experimental tests with test_uart_pico.py
    # anything below 60us was shown to sometimes cause rxbuf overflows
    # with the buffer sizes in use here
    INTER_PACKET_DELAY_MS = None # fails at 1000us, works around 50ms+
    def __init__(self, port:int, baud_rate:int, tx:int, rx:int):
        dttk.Link.__init__(self)
        self._waiting = None
        # for receive resilience, we want a big receive buffer
        # so that if we are busy processing one packet and another arrives,
        # we don't loose it.
        # however, more than about 2 receive packets and we are just kicking the
        # can down the road a bit and delaying the inevitable
        if self.MTU is not None:
            #NOTE, this makes no difference to the reliability of receive
            self._txbuf_size = 0  # write will block until completed
            #NOTE: a 30ms file write could loose packets
            self._rxbuf_size = 512+32  # +32 for pico RX_FIFO
        else: # fallback to safe numbers
            assert False, "buf size default disabled"
            ##self._txbuf_size = 128
            ##self._rxbuf_size = 128

        self._uart = UART(port, baud_rate, txbuf=self._txbuf_size, rxbuf=self._rxbuf_size,
                          timeout=-1, timeout_char=-1, tx=Pin(tx, Pin.OUT), rx=Pin(rx, Pin.OUT))

    def send(self, data:dttk.Buffer or None) -> None:
        """Send data, blocking"""
        #NOTE: if we pass None, this will fail. We clearly never pass None.
        #NOTE: might want to remove None case and pass an empty buffer?
        #it's all about EOF signalling in higher layers
        data.read_with(self._uart.write)
        if self.INTER_PACKET_DELAY_MS is not None:
            ##print("delay %d ms" % self.INTER_PACKET_DELAY_MS)
            utime.sleep_ms(self.INTER_PACKET_DELAY_MS)

    def recvinto(self, buf:dttk.Buffer, info:dict or None=None, wait:bool=False) -> int or None:
        _ = info  # argused
        assert len(buf) == 0, "Uart expects an empty/reset buffer, len was:%d" % len(buf)

        while True:
            if self._uart.any() == 0:
                # no data waiting
                if not wait:
                    ##uart_stats.nodata += 1
                    return 0  # NODATA

            else: # some data waiting
                nb = buf.write_with(self._uart.readinto)  # will clamp to buf size

                uart_stats.update(nb)

                if nb == buf.get_max():
                    ##print("<<RXFULL")
                    uart_stats.rxfull += 1
                return nb

#IDEA: we can probably add a factory method to Packetiser that creates
#a wrapped class with a packetiser on outside
class UartRadio(dttk.Link):
    """A packetised version of a UartLink"""
    #NOTE: no need for a MTU on a stream really, so largest is
    #1 + (255*2) due to how FE & FF expand to 2 bytes with packetiser
    #and all our protocols use a single length byte
    MTU = 1 + (255*2)  #if set to None, no MTU is enforced

    def __init__(self, port:int, baud_rate:int, tx:int, rx:int):
        dttk.Link.__init__(self)
        self._packetiser = dttk.Packetiser(UartLink(port, baud_rate, tx, rx))
        # direct dispatch, faster
        self.send = self._packetiser.send
        self.recvinto = self._packetiser.recvinto


radio = UartRadio(UART_PORT, UART_BAUD_RATE, UART_TX_GP, UART_RX_GP)

link_manager = dttk.LinkManager(radio)

txp = dttk.Progresser("tx").update
##tx_bar = dttk.ProgressBar()

def tx_progress(msg:str or None=None, value:int or None=None) -> None:
    ##if value is not None and msg is not None:
    ##    tx_bar.set_value(value)
    ##    msg = "%s %s" % (str(tx_bar), msg)
    txp(msg)
##tx_progress = None

rxp = dttk.Progresser("rx").update
##rx_bar = dttk.ProgressBar()

def rx_progress(msg:str or None=None, value:int or None=None) -> None:
    ##if value is not None and msg is not None:
    ##    rx_bar.set_value(value)
    ##    msg = "%s %s" % (str(rx_bar), msg)
    rxp(msg)
##rx_progress = None

#----- TRANSFER TASKS ----------------------------------------------------------
def send_file_task(filename:str) -> dttk.Sender: # or exception
    """Non-blocking sender for a single file (as a task that has a tick())"""
    return dttk.FileSender(filename, link_manager, progress_fn=tx_progress, blocksz=BLOCK_SIZE)

def receive_file_task(filename:str) -> dttk.Receiver: # or exception
    """Non-blocking receiver"""
    #NOTE: cached=True is required for Pico local fs due to interrupts disabled on write
    #NOTE2: if you are using an sdcard, you can set cached=False, for immediate writes
    return dttk.FileReceiver(link_manager, filename, progress_fn=rx_progress, cached=True)

#NOTE: TO FIX
# def receive_file_noisy_task(filename:str) -> None: # or exception
#    """Non-blocking receiver with injected noise"""
#    raise ValueError("BROKEN SINCE LAST REFACTOR")
#    # NOISE_SPEC = {"prob": 1, "byte": (1,10)}
#    # noise_gen = dttk.NoiseGenerator(NOISE_SPEC).send
#    # def noisy_receive(info:dict or None=None) -> bytes or None:
#    #     return noise_gen(radio.recvinto(buf, info))
#    # receiver = dttk.FileReceiver(noisy_receive, filename, progress_fn=rx_progress)
#    # return receiver  # has-a tick() and run()

def print_stats(name:str, task) -> None:
    """Host-specific print_stats for sender or receiver"""
    MicroPythonDeps.message("stats for:%s" % name)
    MicroPythonDeps.message("  uart:     %s" % str(uart_stats))
    MicroPythonDeps.message("  link:     %s" % str(dttk.link_stats))
    MicroPythonDeps.message("  pkt:      %s" % str(dttk.packetiser_stats))
    MicroPythonDeps.message("  transfer: %s" % task.get_stats())


#END: ftag_pico.py

