# sdtool.py  28/02/2023  D.J.Whale - SDCard experimentor tool

import sdcard
from utime import ticks_us
import urandom

def hexbytes(buf) -> str:
    """build a run of hex bytes into hexascii"""
    result = []
    for b in buf:
        result.append("%02X" % b)
    return " ".join(result)

def asciibytes(buf) -> str:
    """build a run of ascii characters"""
    result = []
    for b in buf:
        if 32 <= b < 127: result.append(chr(b))
        else:             result.append('.')
    return "".join(result)

def print_block(buf, binary:bool=True, ascii:bool=False, addr:int=0) -> None:
    """Print a block, must be modulo 16 bytes in length"""
    assert len(buf) % 16 == 0
    mv = memoryview(buf)

    def pb(mem, binary:bool=True, ascii:bool=False, addr:int=0):
        for ofs in range(0, len(mem), 16):
            print("%03X: " % (addr+ofs), end="")
            data = mem[ofs:ofs+16]
            if binary: print(hexbytes(data), end=" ")
            if ascii:  print(asciibytes(data), end="")
            print()

    # A whole block is too big for the screen, so provide a MORE option
    pb(mv[:256], binary=binary, ascii=ascii)
    if not input("more?") in ("N", 'n'):
        pb(mv[256:], binary=binary, ascii=ascii, addr=256)

def read_modify_write_verify(lba:int, offset:int, value:int) -> bool:
    """Read a LBA block, modify it, write it, read back and verify"""
    buf = bytearray(512)

    # read
    if not sdcard.readblock(lba, buf):
        print("error(read_write_verify): can't readblock(%d)#1" % lba)
        return False  # ERROR

    # modify
    # U16LE
    buf[offset]   = value & 0xFF
    buf[offset+1] = (value >>8) & 0xFF

    # write
    if not sdcard.writeblock(lba, buf):
        print("error(read_modify_write_verify): Can't writeblock(%d)" % lba)
        return False  # ERROR

    # readback
    if not sdcard.readblock(lba, buf):
        print("error(read_modify_write_verify): Can't readblock(%d)#2" % lba)
        return False  # ERROR

    # verify
    value2 = buf[0] | (buf[1]<<8)  # U16LE
    if value2 != value:
        print("error(read_modify_write_verify): wrote(%04X) but read(%04X)" % (value, value2))
        return False  # ERROR

    return True  # OK

def lltest():
    """Test the basic operation of an SDCard"""
    print("init...")
    if not sdcard.init():
        print("FAIL: can't init card")
        return

    print("signature set to:%s" % str(sdcard.get_signature()))

    #----- CHECK SIZE
    print("get_size_blocks...")
    nblocks = sdcard.get_size_blocks()
    nbytes = sdcard.get_size_bytes()
    if nblocks is None:
        print("FAIL: can't get_size")
        return
    print(f"blocks: {nblocks:,} bytes: {nbytes:,}")

    #----- BLOCK READ AND DISPLAY
    data_block = bytearray(512)

    print("readblock...")
    if not sdcard.readblock(0, data_block):
        print("FAIL: readblock(0)")
        return

    print_block(data_block, ascii=True)

    #---- ZAP BLOCK TO ALL ZEROS
    print("zero_block...")
    buf = bytearray(512)
    if not sdcard.writeblock(0, buf):
        print("FAIL: can't write block to zeros")
        return

    #---- READ/MODIFY/WRITE/VERIFY a block
    print("test_block#1...")
    if not read_modify_write_verify(0, 0, 0xDEAD):
        print("FAIL: can't write/read/verify#1")
        return

    print("test_block#2...")
    if not read_modify_write_verify(0, 0, 0x1234):
        print("FAIL: can't write/read/verify#2")
        return

    #---- EJECT
    sdcard.eject()
    sig = sdcard.get_signature()
    print("ejected, signature now:%s" % str(sig))
    if sig is not None:
        print("FAIL: signature still set, should be None")
        return

    print("PASS")

def connect():
    """Probe SPI and connect to the card"""
    if not sdcard.init():
        print("FAIL: no card found")
    else:
        print("card connected")

def info():
    cid = sdcard.get_cid()
    print("CID:", hexbytes(cid), asciibytes(cid))
    csd = sdcard.get_csd()
    print("CSD:", hexbytes(csd))

def dumpmbr():
    """Dump block 0 of card (master boot record)"""

    buf = memoryview(bytearray(512))
    if not sdcard.readblock(0, buf):
        print("FAIL: can't readblock(0)")

    print_block(buf, ascii=True)

def LE32(buf) -> int:
    assert len(buf) >= 4, "got len:%d" % len(buf)
    return buf[3] << 24 | buf[2] << 16 | buf[1] << 8 | buf[0]

def LE24(buf) -> int:
    assert len(buf) >= 3, "got len:%d" % len(buf)
    return buf[2] << 16 | buf[1] << 8 | buf[0]

# def BE32(buf) -> int:
#     assert len(buf) >= 4, "got len:%d" % len(buf)
#     return buf[0] << 24 | buf[1] << 16 | buf[2] << 8 | buf[3]
#
# def BE24(buf) -> int:
#     assert len(buf) >= 3, "got len:%d" % len(buf)
#     return buf[0] << 16 | buf[1] << 8 | buf[2]

def print_ptab_ent(buf):
    """Print a single partition table record"""
    assert len(buf) >= 16
    # 00            status (or physical drive) bit7 set for active/bootable
    # 01,02,03      CHS address of first absolute sector (FE FF FF for LBA)
    # 04            type (https://www.win.tue.nl/~aeb/partitions/partition_types-1.html) 00=empty
    # 05,06,07      CHS address of last absolute sector
    # 08,09,0A,0B   LBA of first absolute sector
    # 0C,0D,0E,0F   number of sectors in partition

    status    = buf[0x00]
    CHS_first = LE24(buf[0x01:0x03+1])
    type      = buf[0x04]
    CHS_last  = LE24(buf[0x05:0x07+1])
    LBA_first = LE32(buf[0x08:0x0B+1])
    nsectors  = LE32(buf[0x0C:0x0F+1])

    print("f:%02X first:%06X ty:%02X last:%06X LBA:%08X ns:%08X" % (
        status, CHS_first, type, CHS_last, LBA_first, nsectors
    ))

def build_regions() -> tuple: # of Region or None
    """Build 4 regions for the MBR partition table"""
    mbr_r = sdcard.Region(0, 1)
    mbr = memoryview(bytearray(512))
    mbr_r.readinto(0, mbr)

    ptab = mbr[512-2-(16*4):-2]
    ptab_ents = [ptab[ofs:ofs + 16] for ofs in range(0, 64, 16)]

    partitions = [None, None, None, None]
    for i in range(4):
        ent = ptab_ents[i]
        if ent[4] != 0x00:
            partitions[i] = sdcard.Region(LE32(ent[0x08:0x0B+1]), LE32(ent[0x0C:0x0F+1]))

    return tuple(partitions)  # immutable index table

def dumppart():
    """Display the partition table inside the MBR"""
    mbr_r = sdcard.Region(0, 1)
    mbr = memoryview(bytearray(512))
    mbr_r.readinto(0, mbr)

    ptab = mbr[512-2-(16*4):-2]
    ptab_ents = [ptab[ofs:ofs + 16] for ofs in range(0, 64, 16)]

    # raw dump of partition table
    for i in range(4):
        print("p%d:" % i, hexbytes(ptab_ents[i]))
    print()

    # formatted dump of partition table
    partitions = [None, None, None, None]
    for i in range(4):
        ent = ptab_ents[i]
        if ent[4] != 0x00:
            print_ptab_ent(ent)
            partitions[i] = sdcard.Region(LE32(ent[0x08:0x0B+1]), LE32(ent[0x0C:0x0F+1]))
    print()

    # Dump partition regions
    for i in range(4):
        if partitions[i] is None:
            print("%d: unused" % i)
        else:
            print("%d: %s (%d bytes)" % (i, partitions[i], len(partitions[i])*512))

def dumpblock(region: sdcard.Region, ofs: int) -> None:
    """Display one block in a partition"""
    buf = bytearray(512)
    if not region.readinto(ofs, buf):
        print("FAIL: can't read block")
        return

    print_block(buf, ascii=True)

def eject():
    """Eject the card"""
    sdcard.eject()

def write_speed_test(block_no:int):
    """Measure time needed to write a single block"""
    print("write-test with physical block_no:%d" % block_no)
    saved = bytearray(512)
    if not sdcard.readblock(block_no, saved):  # save it for later restore
        print("can't read block:%d" % block_no)
        return

    buf = bytearray(512)
    def speed_test():
        # random buffer each time, to prevent card squashing the write
        for i in range(len(buf)):
            buf[i] = urandom.randint(0, 256)

        start = ticks_us()
        r = sdcard.writeblock(block_no, buf)
        end = ticks_us()
        diff = end - start
        if not r:
            print("can't write block:%d" % block_no)
        return diff

    minv = None
    maxv = None
    sumv = 0
    COUNT = 16
    for _ in range(COUNT):
        write_time = speed_test()
        if minv is None or write_time < minv: minv = write_time
        if maxv is None or write_time > maxv: maxv = write_time
        sumv += write_time

    sdcard.writeblock(block_no, saved)  # restore what was there before

    avg = int(sumv/COUNT)
    print(f"count: {COUNT} avg: {avg:,} us")
    print(f"min time: {minv:,} us")
    print(f"max time: {maxv:,} us")

def run():
    while True:
        try:
            test_no = input("c:connect i:info m:dumpmbr p:dumppart b:dumpblk W:writetst E:eject? ")
            if   test_no == "T": lltest()  # hidden option
            elif test_no == "c": connect()
            elif test_no == 'i': info()
            elif test_no == "m": dumpmbr()
            elif test_no == "p": dumppart()
            elif test_no.startswith("b"):
                try:
                    _, pno, ofs = test_no.split(" ")
                    parts = build_regions()
                    pno = int(pno)
                    ofs = int(ofs)
                    part = parts[pno]
                    if part is None:
                        print("Partition p%d is undefined" % pno)
                    else:
                        dumpblock(part, ofs)
                except ValueError:
                    print("Invalid parameters, try b 0 1  (partition 0, block 1)")

            elif test_no == "E": eject()
            elif test_no == "W":
                write_speed_test(4)  # block 4 is probably block 2 in partition 0
        except sdcard.SDCardError as e:
            print(e)

print("sdtool - SD card experimenter tool")
run()
