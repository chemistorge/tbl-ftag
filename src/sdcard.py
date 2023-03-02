# sdcard.py  23/02/2023  D.J.Whale - test SD card on SPIn

# class SPI
#   read(nbytes, write=0x00) -> bytes:
#   readinto(buf, write=0x00) -> None:
#   write(buf) -> None:
#   write_readinto(write_buf, read_buf) -> None:

# for use on Raspberry Pi Pico with standard MicroPython
from machine import SPI, Pin
from utime import sleep_ms, sleep_us, ticks_ms, ticks_us

SPEED_SLOW_HZ = 100_000
SPEED_FAST_HZ = 1_320_000

SPI_N    = 1
GP_SCK   = 10  # output
GP_MOSI  = 11  # output
GP_MISO  = 12  # input
GP_CS    = 13  # output

# STORED STATE
cdv        = None # set in init_card to 1 or 512
cmdbuf     = memoryview(bytearray(16))
buf1       = cmdbuf[:1]
start_lba  = 0
num_lba    = None  # read from CSD record later
signature  = None  # filled in in init(), to detect card ejects

# init SPI
spi = SPI(SPI_N, baudrate=SPEED_SLOW_HZ, polarity=0, phase=0, bits=8,
          sck=Pin(GP_SCK), mosi=Pin(GP_MOSI), miso=Pin(GP_MISO))

# chip select idles high when bus inactive
spi_cs = Pin(GP_CS, Pin.OUT)
spi_cs.high()  # deselected

R1_IDLE_STATE         = 1<<0
R1_ILLEGAL_COMMAND    = 1<<2
DRT_ACCEPTED          = 0b000_010_1  # data_response_token
INIT_RETRY_TIMES      = 100  # 100 * 50ms = 5 seconds max
INIT_RETRY_DELAY_MS   = 50
TIMEOUT_OF_CMD_US     = 5_000 # 5ms for any single command
TIMEOUT_WRITE_MS      = 200  # 99,380us measured on bench

# cmd, arg, crc, [final_ff=0], [release=True]
CMD_INIT                  = (0, 0, 0x95)
CMD_GET_CARD_VER          = (8, 0x01aa, 0x87, 4)
CMD_READ_OCR_ND           = (58, 0, 0, 4)
CMD_SEND_CSD_DATA         = (9, 0, 0, 0, False)
CMD_SEND_CID_DATA         = (10, 0, 0, 0, False)
CMD_SET_BLOCKLEN_512      = (16, 512, 0)
CMDFN_READ_SINGLE_BLOCK   = lambda bn: (17, bn*cdv, 0)
CMDFN_READ_MULTIPLE_BLOCK = lambda bn: (18, bn*cdv, 0)
CMDFN_WRITE_BLOCK         = lambda bn: (24, bn*cdv, 0, 0, False)
TOKEN_DATA = 0xFE

CMDND_STOP_TRANSMISSION   = (12, )

CMD_APP_CMD               = (55, 0, 0)
ACMD_SD_SEND_OP_COND0     = (41, 0, 0)
ACMD_SD_SEND_OP_COND4     = (41, 0x4000_0000, 0)

class SDCardError(Exception): pass

def init() -> bool:
    """Probe and initialise a connection to a possible SDCard"""
    global start_lba, num_lba, signature

    ##print("probing...")
    signature = None
    low_speed()
    card_version = None
    for _ in range(2):
        card_version = probe_card()
        if card_version is not None: break

    if card_version is None:
        print("error(init): no sdcard found")
        return False  # ERROR
    ##print("card version:%d" % card_version)

    if   card_version == 1: init_cardV1()
    elif card_version == 2: init_cardV2()
    else:
        print("error(init): Unknown card version:%d" % card_version)
        return False  # ERROR

    ##print("get_csd...")
    csd = get_csd()
    if csd is None:
        print("error(init): get_csd()")
        return False  # ERROR

    start_lba = 0
    num_lba   = parse_num_blocks(csd)
    #print(f"nblocks={nblocks:,} ({nblocks*512:,} bytes)")

    set_block_length()  # always 512 on V2 card
    high_speed()
    signature = ticks_ms()  # time of successful mount
    return True  # OK

def eject() -> None:
    """Invalidate any connection to a SDCard"""
    global cdv, start_lba, num_lba, signature
    cdv       = None
    start_lba = None
    num_lba   = None
    signature = None

def get_signature() -> int or None:
    """Get a unique signature for this mount, None if not known"""
    global signature
    # This can be used to later detect card ejects
    return signature

def get_size_blocks() -> int or None:
    """Get the size of this card in 512 byte LBA blocks"""
    csd = get_csd()
    if not csd:
        print("error(get_size_bytes): can't get_csd()")
        return None  # ERROR

    return parse_num_blocks(csd)

def get_size_bytes() -> int or None:
    """Get the size of this card in bytes"""
    s = get_size_blocks()
    if s is None: return s
    return s * 512

# used by writeblocks()
# def cmd_nodata(cmd) -> bool:
#     """Send a command that has no data"""
#     spi_cs.low()
#     spi.read(1, cmd)
#     spi.read(1, 0xFF)  # ignore stuff byte
#     timeout_at = ticks_us() + TIMEOUT_CMD_US
#     while ticks_us() < timeout_at:
#         spi.readinto(buf1, 0xFF)
#         if 0xFF == buf1[0]:  # or, check high bit??
#             spi_cs.high()
#             spi.read(1, 0xFF)
#             return True  # OK
#     spi_cs.high()
#     spi.read(1, 0xFF)
#     print("error: timeout in cmd_nodata")
#     return False  # TIMEOUT

# def time_fn(fn:callable) -> callable:
#     def timeit(*args, **kwargs):
#         start = ticks_us()
#         res = fn(*args, **kwargs)
#         end = ticks_us()
#         diff = end - start
#         print(diff)
#         return res
#     return timeit

def cmd(cmdno:int, arg:int, crc:int, final_ff:int=0, release:bool=True) -> int or None:
    """Create and send a command"""
    spi_cs.low()

    txbuf = cmdbuf[:6]
    txbuf[0] = 0x40 | cmdno
    txbuf[1] = arg >> 24
    txbuf[2] = arg >> 16
    txbuf[3] = arg >> 8
    txbuf[4] = arg
    txbuf[5] = crc
    spi.write(txbuf)

    # busy-wait for response bit7==0
    timeout_at = ticks_us() + TIMEOUT_OF_CMD_US
    while ticks_us() < timeout_at:
        spi.readinto(buf1, 0xFF)
        response = buf1[0]
        if not (response & 0x80):
            if final_ff != 0: spi.read(final_ff, 0xFF)
            if release:
                spi_cs.high()
                spi.read(1, 0xFF)
            return response

    # timeout
    spi_cs.high()
    spi.read(1, 0xFF)
    print("error: CMD%d timeout" % cmd)
    return None  # NO_RESPONSE

def write(token, buf) -> bool:
    """Write a data block and check it was accepted"""
    assert len(buf) == 512
    spi_cs.low()

    # send: start of block, data, checksum
    spi.read(1, token)
    spi.write(buf)
    spi.read(2, 0xFF)  # skip checksum word

    # check the response
    spi.readinto(buf1, 0xFF)
    response = buf1[0]
    if response & 0x1F != DRT_ACCEPTED:
        spi_cs.high()
        spi.read(1, 0xFF)
        print("error(write):wrong response, expect:05, got:%02X" % response)
        return False  # ERROR

    # wait for write to finish
    timeout_at = ticks_ms() + TIMEOUT_WRITE_MS
    while ticks_ms() < timeout_at:
        spi.readinto(buf1, 0xFF)
        if buf1[0] != 0:
            spi_cs.high()
            spi.read(1, 0xFF)
            return True  # OK

    print("error(write): timeout after %d ms" % TIMEOUT_WRITE_MS)
    return False  # TIMEOUT

def readinto(buf):
    """Read a data block"""
    spi_cs.low()

    # read until start byte
    while True:
        spi.readinto(buf1, 0xFF)
        if buf1[0] == 0xFE: break

    # read data
    spi.readinto(buf, 0xFF)

    # skip checksum word
    spi.read(2, 0xFF)

    spi_cs.high()
    spi.read(1, 0xFF)

def probe_card() -> int or None:  # CARD_VERSION | UNKNOWN
    """See if a card is present, what version is it?"""
    # clock card at least 100 cycles with cs high
    #NOTE: no idea why this is needed, is this to flush the cmd pipeline?
    #there was no mention of this in the sdcard.org spec
    #but the micropython driver does it.
    spi.read(16, 0xFF)

    for _ in range(5):
        if cmd(*CMD_INIT) == R1_IDLE_STATE: break
    else:
        ##print("error(probe_card): no response from CMD_INIT")
        return None  # NO SDCARD

    r = cmd(*CMD_GET_CARD_VER)
    if r == R1_IDLE_STATE:
        return 2  # V2 CARD
    elif r == R1_IDLE_STATE | R1_ILLEGAL_COMMAND:
        return 1  # V1 CARD
    else:
        print("error(probe_card): unknown SD card version (rsp=%02X)" % r)
        return 0xFF  # UNKNOWN SD CARD VER

def init_cardV1() -> bool:
    """Initialise a card known to be a V1 card"""
    global cdv
    for _ in range(INIT_RETRY_TIMES):
        cmd(*CMD_APP_CMD)
        if cmd(*ACMD_SD_SEND_OP_COND0) == 0:
            ##print("V1, cdv=512")
            cdv = 512
            return True  # OK
    print("error(init_cardV1): timeout V1")
    return False  # TIMEOUT

def init_cardV2() -> bool:
    """Initialise a card known to be a V2 card"""
    global cdv
    for _ in range(INIT_RETRY_TIMES):
        cmd(*CMD_READ_OCR_ND)
        cmd(*CMD_APP_CMD)
        if 0 == cmd(*ACMD_SD_SEND_OP_COND4):
            cmd(*CMD_READ_OCR_ND)
            ##print("V2, cdv=1")
            cdv = 1
            return True  # OK
        sleep_ms(INIT_RETRY_DELAY_MS)
    print("error(init_cardV2): timeout V2")
    return False  # TIMEOUT

def get_cid() -> bytes or None:
    """Read the CID record"""
    if 0 != cmd(*CMD_SEND_CID_DATA):
        print("error(get_cid): no response")
        return None
    cid = bytearray(16)
    readinto(cid)
    return bytes(cid)  # immutable

def get_csd() -> bytes or None:
    """Read the CSD record"""
    if 0 != cmd(*CMD_SEND_CSD_DATA):
        print("error(get_csd): no response")
        return None
    csd = bytearray(16)
    readinto(csd)

    if csd[0] & 0xc0 != 0x40: #CSD_STRUCTURE b01 == CSD version 2.0
        print("error(get_num_sectors): did not get a V2 CSD_STRUCTURE")
        return None  # ERROR
    return bytes(csd)  # immutable

def parse_num_blocks(csd:bytes) -> int:
    """Parse the C_SIZE field out as a number of 512 byte blocks on the card"""
    # C_SIZE upper 6 always zero, so this is 16 bits
    # capacity = (CSIZE+1) * 512KByte   i.e.: * 524288 = 0x8_0000 = 512KB
    # actual CSD_SIZE_MULT always 512Kbyte in version 2 record
    # CSD records are big-endian
    CSIZE = ((csd[8] << 8 | csd[9]) + 1)  # multiply by  512KB
    ##print("CSIZE:%d (%04X)" % (CSIZE, CSIZE))
    ##nbytes = (CSIZE * 512 * 1024) / 512
    return CSIZE * 1024

def set_block_length() -> bool:
    """Set the block transfer length for block reads and writes"""
    if cmd(*CMD_SET_BLOCKLEN_512) != 0:
        print("error(set_block_length): can't set block length")
        return False  # FAILED
    return True  # OK

def high_speed():
    """Move to high speed SPI, now card is initialised"""
    spi.init(baudrate=SPEED_FAST_HZ, phase=0, polarity=0)

def low_speed():
    """Move to low speed SPI, for card probing"""
    spi.init(baudrate=SPEED_SLOW_HZ, phase=0, polarity=0)

def readblock(block_num:int, buf) -> bool:
    """Read a whole logical block into provided buffer"""
    assert len(buf) == 512, "readblock: wrong block size, want:512, got:%d" % len(buf)
    if 0 != cmd(*CMDFN_READ_SINGLE_BLOCK(block_num)):
        return False  # ERROR
    # receive the data
    readinto(buf)
    return True  # OK

# NOT YET TESTED
# def readblocks(block_num:int, buf) -> bool:
#     nblocks, rem = divmod(len(buf), 512)
#     assert nblocks and not rem, "readblocks: invalid non zero remainder:%d" % rem
#     if nblocks == 1:
#         return readblock(block_num, buf)
#     else:
#         if 0 != cmd(*CMDFN_READ_MULTIPLE_BLOCK(block_num)):
#             return False  # ERROR
#         offset = 0
#         mv = memoryview(buf)
#         while nblocks:
#             readinto(mv[offset : offset + 512])
#             offset += 512
#             nblocks -= 1
#         return cmd_nodata(CMDND_STOP_TRANSMISSION)

def writeblock(block_num:int, buf) -> bool:
    """Write a whole logical block to the card"""
    assert len(buf) % 512 == 0
    response = cmd(*CMDFN_WRITE_BLOCK(block_num))
    if response != 0:
        print("error(writeblock): CMD_WRITE_BLOCK failed with %02X" % response)
        return False  # ERROR

    # send the data
    return write(TOKEN_DATA, buf)

#----- REGION - for a range of blocks on a device ------------------------------

class Region:
    def __init__(self, r_start:int=0, r_size:int or None=None):
        assert r_start is not None
        card_sig = get_signature()
        if card_sig is None: raise SDCardError("sdcard not mounted")

        card_blocks = get_size_blocks()
        assert card_blocks is not None

        # validate start
        if r_start < 0 or r_start >= card_blocks:
            raise ValueError("start out of range: got:%d max:%d" % (r_start, card_blocks-1))

        max_size = card_blocks - r_start
        if r_size is None: r_size = max_size

        # validate num_blocks
        if r_size > max_size:
            raise ValueError("num_blocks out of range: got:%d max:%d" % (r_size, max_size))

        # update state
        self._start     = r_start
        self._size      = r_size
        self._signature = card_sig

    def __repr__(self) -> str:
        return "Region(r_start=%s, r_size=%s)" % (str(self._start), str(self._size))

    def __len__(self) -> int:
        """The total number of 512 byte blocks in this region"""
        return self._size

    def __getitem__(self, idx):
        """Get a constricted subset of this existing region"""
        # e.g. a partition inside a device, or a file inside a partition
        if self._signature != get_signature(): raise SDCardError("card has been ejected")
        if isinstance(idx, int):
            # a single block
            start = idx
            size = 1
        else:
            # slice, a range of blocks within this region
            start = idx.start
            size  = idx.stop - idx.start

        # validate
        if start >= self._size or start < 0:
            raise ValueError("start out of range: got:%d max:%d" % (start, self._size))
        max_ofs = self._size - start
        if size > max_ofs or size < 0:
            raise ValueError("size out of range: got:%d max:%d" % (size, max_ofs))

        return Region(self._start + start, size)

    def readinto(self, offset, buf) -> bool:
        if self._signature != get_signature(): raise SDCardError("card has been changed")
        assert offset < self._size, "Invalid offset, got:%d max:%d" % (offset, self._size-1)
        return readblock(self._start+offset, buf)

    def write(self, offset, buf) -> bool:
        if self._signature != get_signature(): raise SDCardError("card has been changed")
        assert offset < self._size, "Invalid offset, got:%d max:%d" % (offset, self._size-1)
        return writeblock(self._start+offset, buf)

