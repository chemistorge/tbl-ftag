# ftag_pico.py  22/01/2023  D.J.Whale - pico based adaptor to file transfer agent
#NOTE: for use on PICO micropython only
# it sets the deps for the dttk module
# but in this module, it can use functions directly

import platdeps
from platdeps import micropython
import myboard

import dttk
from machine import UART, Pin
import perf

# radio is an optional component
try:
    from radio import RadioISM
except ImportError:
    RadioISM = None

print("OPTION=%s" % myboard.OPTION)


#----- UART PHY ----------------------------------------------------------------
class UStats:
    def __init__(self):
        ##self.data = 0
        ##self.nodata = 0
        self.rxfull = 0
        self.minbytes = None
        self.maxbytes = None
        ##self.rdsizes  = []
        self._updated = False

    def update(self, nb:int) -> None:
        self._updated = True
        ##self.data += 1
        # MINMAX for what we read in each chunk from the uart peripheral
        if self.minbytes is None:
            self.minbytes = nb
        elif nb < self.minbytes:
            self.minbytes = nb

        if self.maxbytes is None:
            self.maxbytes = nb
        elif nb > self.maxbytes:
            self.maxbytes = nb

        ## keep a list of read sizes into the buffer
        ##DISABLED self.rdsizes.append(nb)

    def has_data(self) -> bool:
        return self._updated

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
            platdeps.time_sleep_ms(self.INTER_PACKET_DELAY_MS)

    def recvinto(self, buf:dttk.Buffer, info:dict or None=None, wait:int=0) -> int or None:
        _ = info  # argused
        assert len(buf) == 0, "Uart expects an empty/reset buffer, len was:%d" % len(buf)

        ends_at = platdeps.time_ms() + wait
        while True:
            if self._uart.any() > 0:
                # some data waiting
                nb = buf.write_with(self._uart.readinto)  # will clamp to buf size
                uart_stats.update(nb)

                if nb == buf.get_max():
                    ##print("<<RXFULL")
                    uart_stats.rxfull += 1
                return nb

            else:
                # no data waiting
                if platdeps.time_ms() >= ends_at:
                    ##uart_stats.nodata += 1
                    return 0  # NODATA


#IDEA: we can probably add a factory method to Packetiser that creates
#a wrapped class with a packetiser on outside
class PacketisedUart(dttk.Link):
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


#----- GENERIC SETUP -----------------------------------------------------------

def get_phy():
    """Get the physical link - configurable"""
    while True:
        while True:
            choice = input("[U]ART or [R]adio [UR]?")
            if choice in ('U', 'R', 'u', 'r'):
                choice = choice.upper()
                break

        if choice == 'U':
            packetised_uart = PacketisedUart(
                myboard.UartCfg.PORT, myboard.UartCfg.BAUD_RATE,
                myboard.UartCfg.TX_GPN, myboard.UartCfg.RX_GPN)
            return packetised_uart

        if choice == 'R':
            if RadioISM is None:
                print("Radio not present")
                continue
            else:
                radio = RadioISM()
                radio.on()
                return radio

        assert False  # should not get here

link_manager = dttk.LinkManager(get_phy())

txp = dttk.Progresser("tx").update
##tx_bar = dttk.ProgressBar()

def tx_progress(msg:str or None=None, value:int or None=None) -> None:
    _ = value  # argused
    ##if value is not None and msg is not None:
    ##    tx_bar.set_value(value)
    ##    msg = "%s %s" % (str(tx_bar), msg)
    txp(msg)
##tx_progress = None

rxp = dttk.Progresser("rx").update
##rx_bar = dttk.ProgressBar()

def rx_progress(msg:str or None=None, value:int or None=None) -> None:
    _ = value  # argused
    ##if value is not None and msg is not None:
    ##    rx_bar.set_value(value)
    ##    msg = "%s %s" % (str(rx_bar), msg)
    rxp(msg)
##rx_progress = None


#----- TRANSFER TASKS ----------------------------------------------------------
def send_file_task(filename:str, progress=None) -> dttk.Sender: # or exception
    """Non-blocking sender for a single file (as a task that has a tick())"""
    if progress is None: progress = tx_progress
    return dttk.FileSender(filename, link_manager, progress_fn=progress, blocksz=myboard.UartCfg.BLOCK_SIZE)

def receive_file_task(filename:str, progress=None) -> dttk.Receiver: # or exception
    """Non-blocking receiver"""
    #NOTE: cached=True is required for Pico local fs due to interrupts disabled on write
    #NOTE2: if you are using an sdcard, you can set cached=False, for immediate writes
    if progress is None: progress=rx_progress
    return dttk.FileReceiver(link_manager, filename, progress_fn=progress, cached=True)

#NOTE: TO FIX
# def receive_file_noisy_task(filename:str) -> None: # or exception
#    """Non-blocking receiver with injected noise"""
#    raise ValueError("BROKEN SINCE LAST REFACTOR")
#    # NOISE_SPEC = {"prob": 1, "byte": (1,10)}
#    # noise_gen = dttk.NoiseGenerator(NOISE_SPEC).send
#    # def noisy_receive(info:dict or None=None) -> bytes or None:
#    #     return noise_gen(packetised_uart.recvinto(buf, info))
#    # receiver = dttk.FileReceiver(noisy_receive, filename, progress_fn=rx_progress)
#    # return receiver  # has-a tick() and run()

def print_stats(name:str or None=None, task=None) -> None:
    """Pico-specific print_stats for sender or receiver"""
    if name is not None:                 platdeps.message("STATS:%s" % name)
    if uart_stats.has_data():            platdeps.message("uart: %s" % str(uart_stats))
    if dttk.link_stats.has_data():       platdeps.message("link: %s" % str(dttk.link_stats))
    if dttk.packetiser_stats.has_data(): platdeps.message("pkt:  %s" % str(dttk.packetiser_stats))
    if task is not None:                 platdeps.message("xfer: %s" % task.get_stats())

#END: ftag_pico.py

