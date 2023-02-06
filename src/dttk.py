# dttk.py  06/01/2023  D.J.Whale - data transfer toolkit
# This module uses dependency injection, so it can work on multiple platforms.

import random  # available on host and pico
import perf
#IDEA, if don't import it, define perf as a scaffold here
#and if we do import it, turn it on, always.
#e.g. import perf or import no_perf as perf
import gc

#----- PLATFORM DEPENDENCIES (INJECTED) ----------------------------------------

# message, filesize, os_path_basename, os_rename, hashlib_sha256, time_time
deps = None
def set_deps(d) -> None:
    global deps
    deps = d
    perf.set_deps(d)

#----- SUPPORT CLASSES AND METHODS ---------------------------------------------
class ProgressBar:
    def __init__(self, max_value:int or None=None, width:int or None=None, show_number:bool=True):
        self._value = 0
        self._max_value = max_value if max_value is not None else 100
        self._width = width if width is not None else 20
        self._show_number = show_number

    def reset(self) -> None:
        """Reset to zero"""
        self.set_value(0)

    def set_value(self, value:int) -> None:
        """Set the current progress value"""
        self._value = value
        # cap to max/min
        if self._value > self._max_value:
            self._value = self._max_value
        elif self._value < 0:
            self._value = 0

    def get_value(self) -> int:
        """Get the current value 0..max_value"""
        return self._value

    def get_max_value(self) -> int:
        """Get the max value"""
        return self._max_value

    def get_percent(self) -> int:
        """Get a percent, 0..100"""
        return int((self._value / self._max_value)*100)

    def __str__(self) -> str:
        """Get a bar scaled to width"""
        p = self.get_percent()
        scale  = 100 / self._width
        length = int(p / scale)
        bar    = "#" * length
        dots   = "." * (self._width - length)
        ##return "[%s%s] (v:%d p:%d mv:%d wd:%d)" % (bar, dots, self._value, p, self._max_value, self._width)
        if self._show_number:
            return "[%s%s] (%d%%)" % (bar, dots, p)
        return "[%s%s]" % (bar, dots)

class Progresser:
    """Display progress information on a single terminal line"""
    MAXLEN = 79
    _SPACES = ' ' * MAXLEN

    def __init__(self, name:str or None=None, stream=None, rate=1):
        if name is not None: name += ':'
        else:                name = ""
        self._name = name
        self._stream = stream
        self._last_len = 0
        self._rate = rate
        self._next = deps.time_time() + rate

    def __call__(self, *args, **kwargs):
        return self.update(*args, **kwargs)

    def output(self, msg:str) -> None:
        if self._stream is not None: self._stream.write(msg)
        else: print(msg, end="")

    def update(self, msg:str or None=None, value:int or None=None) -> None:
        """Update the progress line, clear it, or start a new line below"""
        _ = value  # argused
        if msg is None:
            # clear existing line
            self.output("\r%s\r" % self._SPACES)
            self._last_len = 0

        elif msg == "\n":
            # preserve existing line, move to next line
            self.output("\n")
            self._last_len = 0

        else:
            def time_to_output() -> bool:
                if self._rate is None: return True
                now = deps.time_time()
                if now >= self._next:
                    self._next = now + self._rate
                    return True
                return False

            # overwrite existing line
            if time_to_output():
                self.output(self._SPACES)  # clear line
                line = "\r%s%s" % (self._name, msg)
                this_len = len(line)
                if this_len > self.MAXLEN:
                    line = line[:self.MAXLEN]  #NOTE: possibly expensive
                    this_len = self.MAXLEN

                self.output("%s\r" % line)
                self._last_len = this_len

#NOTE: needs moving over to Buffer
class NoiseGenerator:
    def __init__(self, spec:dict or None=None):
        self._spec = spec

    #NOTE: Buffer?
    def send(self, data):
        if data is None: return None    # pass forward EOF
        if len(data) == 0: return data  # pass forward NODATA
        return self.add_noise(data, self._spec)

    #NOTE: Buffer?
    @staticmethod
    def add_noise(data, spec:dict or None=None):
        ##assert data is not None
        if spec is None: return data  # no-errors
        if "prob" in spec: # 0..100, from impossible to definitely
            prob = spec["prob"]
            # if 25 % probability, then numbers 1..25 will be a hit
            if random.randint(1, 100) <= prob:
                pass # got a hit, will introduce error
            else:
                return data  # miss, won't do it

        # introduce error(s) according to spec
        if "drop" in spec:
            drop_perc = spec['drop']
            if random.randint(1, 100) <= drop_perc:
                # got a hit, drop the packet
                return b'' # no data available
            # keep going, look at non-drop errors

        # introduce data errors according to spec
        new_data = data

        # optionally introduce length errors
        if "len" in spec:
            #  drop up to 4 random bytes at end
            #    {"len":(-4, 0)}
            #  add up to 4random bytes at end
            #    {"len":(0, +4)}
            #  drop or add bytes at end
            #    {"len": (-4, +4)}

            lspec = spec["len"]
            trunc, extend = lspec
            # if drop and extend, decide which to do
            if trunc != 0 and extend != 0:
                do_trunc = random.choice([True, False])
            else:
                do_trunc = (trunc != 0)

            if do_trunc:
                amt = random.randint(0, -trunc)
                amt = min(amt, len(new_data))
                for i in range(amt):
                    new_data.pop()

            else: # extend
                amt = random.randint(0, extend)
                for i in range(amt):
                    new_data.append(random.randint(0, 255))

        # optionally introduce bit errors
        if "bit" in spec:
            #  m bit flips at random distances
            #    {"bit": (5, 0)}
            #  n bit flips at bit distance d
            #    {"bit": (5, 10)}

            bspec = spec["bit"]
            num, dist = bspec
            nbits = len(new_data)*8
            bitpos = random.randint(0, nbits-1)  # start at a random bit
            for n in range(num):
                bytepos = int(bitpos / 8)
                b =       int(bitpos % 8)
                new_data[bytepos] ^= (1<<b)  # flip the bit
                if dist == 0: bitpos = (bitpos + random.randint(1, nbits)) % nbits
                else:         bitpos = (bitpos + dist) % nbits

        # optionally introduce byte errors
        if "byte" in spec:
            #  n random byte corruptions at random distances
            #    {"byte": (3, 0)}
            #  n random byte corruptions at byte distance d
            #    {"byte", (3, 2)}
            bspec = spec["byte"]
            num, dist = bspec
            nbytes = len(new_data)
            bytepos = random.randint(0, nbytes-1)  # start at a random byte
            for n in range(num):
                new_data[bytepos] ^= random.randint(1, 255)
                if dist == 0: bytepos = (bytepos + random.randint(1, nbytes)) % nbytes
                else:         bytepos = (bytepos + dist) % nbytes

        return new_data

class BitSet:
    """A set of bits, packed efficiently into words"""
    WORD_SIZE = 8

    def __init__(self, nflags:int) -> None:
        self._nflags    = nflags
        self._nsetflags = 0
        self._flags = bytearray(nflags)

    def __len__(self) -> int:
        return self._nflags

    def _indexof(self,flag:int) -> tuple: # of (wordidx:int, bitidx:int)
        """Get the list index of this flag"""
        return int(flag / self.WORD_SIZE), flag % self.WORD_SIZE

    def  __getitem__(self, index:int) -> bool:
        """Get the status of a flag at a specific index"""
        ##if not (0 <= index < self._nflags): raise IndexError("item index %s is out of range" % str(index))
        word, bit = self._indexof(index)
        if word >= len(self._flags): return False  # all flags default to clear
        return (self._flags[word] & (1<<bit)) != 0

    def __setitem__(self, index:int, value:bool or int) -> None:
        """Set or clear the flag at this index"""
        ##if not (0 <= index < self._nflags): raise IndexError("item index %s is out of range" % str(index))
        ##assert isinstance(value, (bool, int)), "expected type:(bool, int), got:%s" % str(type(value))
        if isinstance(value, bool): value = bool(value)
        word, bit = self._indexof(index)

        w = self._flags[word]
        bitmask = 1<<bit
        if value: w2 = w | bitmask
        else:     w2 = w & ~ bitmask

        if w != w2:
            # only update, if there was a change
            if value: self._nsetflags += 1
            else:     self._nsetflags -= 1
            ##assert 0 <= self._nsetflags <= self._nflags, "nsetflags corrupted? %d max %d" % (self._nsetflags, self._nflags)
            self._flags[word] = w2
            ##deps.message(self._flags)

    def __str__(self) -> str:
        """Get a string representation of all bits"""
        res = []
        for i in range(self._nflags):
            res.append("1" if self[i] else "0")
        return "".join(res)

    def is_complete(self) -> bool:
        """If all nflags flags are set, returns True"""
        return self._nsetflags == self._nflags

    def get_percent(self) -> int:
        """Get percentage full 0..100% where 100% is always 'full'"""
        # useful for progress displays
        if self.is_complete(): return 100  # no rounding errors here
        #NOTE: scale up by 100 as an int, rather than using a float
        perc = float(self._nsetflags) / float(self._nflags)
        perc = int(perc * 100)
        if perc == 100: perc = 99  # no rounding errors here
        return perc

def crc16(data, length:int or None=None) -> int:
    """calculates a CCITT-16 CRC"""
    CRC16_POLY = 0x1021  # CCITT-16
    if length is None: length = len(data)
    crcsum = 0xFFFF

    for idx in range(length):
        # add_byte
        v = 0x80
        for _ in range(8):
            this_byte = data[idx]
            bit = crcsum & 0x8000
            crcsum <<= 1
            if this_byte & v:  crcsum += 1
            if bit:            crcsum ^= CRC16_POLY
            v >>= 1

    # finish
    for i in range(16):
        bit = crcsum & 0x8000
        crcsum <<= 1
        if bit: crcsum ^= CRC16_POLY
    return crcsum & 0xFFFF  # keep within a U16


#----- SUPPORT FUNCTIONS -------------------------------------------------------

def bin_to_hex(data) -> str or None:
    """Convert a run of binary bytes into a single line of hexascii"""
    if data is None: return None
    if len(data) == 0: return ""

    result = []
    first = True
    for b in data:
        if not first: result.append(" ")
        else:         first = False
        result.append("%02X" % b)
    return "".join(result)

def hex_to_bin(in_hex:str):
    """Convert a line of hex string to a run of bytes"""
    #NOTE: don't throw exceptions, try to keep going
    #as a higher layer error detection will catch duff data
    out_bin = bytearray()
    pos = 0
    while pos < len(in_hex):
        # skip ws
        if in_hex[pos] in " \t\r\n":
            pos += 1
            continue

        # read 2 hex, or error
        if pos+1 >= len(in_hex):
            ##deps.message("warning:hex line is truncated?\n")
            break  # just return what we got

        def hexch(ch:str) -> int:
            """Parse a single char assuming it is hexascii"""
            ##assert len(ch) == 1
            if '0' <= ch <= '9': return ord(ch) - ord('0')
            if 'a' <= ch <= 'f': return ord(ch) - ord('a') + 10
            if 'A' <= ch <= 'F': return ord(ch) - ord('A') + 10
            ##deps.message("warning:invalid hex char (0x%02X) %c\n" % (ord(ch), ch))
            return 0  # try to keep going

        h = (hexch(in_hex[pos]) << 4) | hexch(in_hex[pos+1])
        out_bin.append(h)
        pos += 2

    return out_bin

def hexstr(data) -> str:
    """Print a run of bytes as a hexascii string"""
    if data is None: return ""
    res = []
    for b in data:
        res.append ("%02X" % b)
    return "".join(res)

def hashstr(the_hash) -> str:
    if len(the_hash) > 4:
        return "%02X%02X...%02X%02X" % (the_hash[0], the_hash[1], the_hash[-2], the_hash[-1])
    else:
        return hexstr(the_hash)

def get_file_info(filename:str) -> tuple: # (filesize:int, sha256:bytes)
    """File size and SHA256 of a file"""

    def sha256_of_file(filename2: str):
        """Calculate SHA256, as if we did:shasum -a 256 filename.bin"""
        hasher = deps.hashlib_sha256()
        with open(filename2, "rb") as f:
            while True:  #NOTE: pico iter() works differently
                block = f.read(512)  # typical cluster size on a SDcard
                if not block: break  #EOF
                hasher.update(block)
        digest = hasher.digest()
        ##assert len(digest) == 32
        return digest

    sz     = deps.filesize(filename)
    sha256 = sha256_of_file(filename)
    return sz, sha256

high = lambda b: (b & 0xFF00) >> 8
low  = lambda b: b & 0xFF

#===== EFFICIENT MEMORY BUFFERS ================================================

class Buffer:
    """A high performance, low copy overhead buffer for packets"""
    # use this, instead of mixing bytes and bytearray, to avoid copy overhead
    #NOTE: this implements the key buffer protocol methods, so it can be
    #used mostly where a bytes() or a bytearray() is used, interchangeably.

    DEFAULT_START = 10  # space for prepending headers
    DEFAULT_SIZE  = 128

    def __init__(self, values=None, size:int=DEFAULT_SIZE, start=DEFAULT_START):
        self._buf = bytearray(size)
        self._initial_start = self._start = self._end = start
        if values is not None:  self.create_from(values)

    def __iter__(self):
        """Create an iterator for cycling through all active bytes"""
        class BufferIter:
            def __init__(self, parent):
                self._parent = parent
                self._next_idx = 0

            def __iter__(self):
                return self

            def __next__(self) -> int:
                if self._next_idx >= len(self._parent): raise StopIteration
                v = self._parent[self._next_idx]
                self._next_idx += 1
                return v

        return BufferIter(self)

    def __str__(self) -> str:
        """Show stats about the buffer"""
        return "Buffer(sz:%d, start:%d, end:%d)" % (
            len(self._buf), self._start, self._end)

    def __getitem__(self, idx:int): # -> bytes #NOTE int might be better?
        return self._buf[self._start + idx]

    def __len__(self) -> int:
        """The current used length, between start and end"""
        return self._end - self._start

    def get_max(self) -> int:
        """The maximum size of buffer"""
        return len(self._buf)

    def is_full(self) -> bool:
        """Is this buffer full, so an extend or prepend will grow()?"""
        return (self._end - self._start) == len(self._buf)

    def get_slice(self, start:int, length:int) -> bytearray:
        """Read a slice of the buffer, e.g. to get a SHA256 or filename out"""
        s = self._start+start
        return self._buf[s:s+length]

    def read_with(self, user_fn:callable) -> int or None:
        """Access the internal buffer valid range, using a user provided function"""
        # This prevents the need to expose the buffer to outside
        # this will write with the uart in the pico tester
        nb = user_fn(self._buf[self._start:self._end])
        #NOTE: this takes a slice of the buffer if start and end are not full range
        #and that can stress out the garbage collector
        ##deps.message("read_with user_fn wrote:%s" % str(nb))
        return nb

    def write_with(self, user_fn:callable) -> int or None:
        """Use the user function to read into our buffer"""
        # This prevents exposing our buffer to outsiders
        # it always reads to the start of the buffer at zero, but that is fine
        # because this will be for a receive path which will peel off headers
        # and never need to lgrow()
        self._start = self._end = 0
        nb = user_fn(self._buf)
        if nb is None: return None  # could not read (probably EOF?)
        self._end = nb
        return nb

    def create_from(self, values) -> None:
        """Create a buffer filled with these values"""
        self.reset()
        self.extend(values)

    def prepend1(self, value) -> None:
        self._start -= 1
        self._buf[self._start] = value

    def prepend(self, values) -> None:
        """Prepend one or more values to the LHS, e.g. adding a header"""
        self._start -= len(values)
        offset = self._start
        b = self._buf
        for v in values:  # assumes iterable
            b[offset] = v  # will fail if not big enough, or if value out of range
            offset += 1

    def append(self, value:int) -> None:
        """Same as extend"""
        self._buf[self._end] = value
        self._end += 1

    def extend(self, values) -> None:
        """Extend one or more values to the RHS, e.g. adding a footer"""
        offset = self._end
        b = self._buf
        for v in values:  # assumes iterable
            b[offset] = v  # will fail if not big enough, or if value out of range
            offset += 1
        self._end = offset

    def ltrunc(self, amount:int) -> None:
        """Remove bytes at LHS, e.g. to remove a header that has been processed"""
        self._start += amount

    def rtrunc(self, amount:int) -> None:
        """Remove bytes at RHS, e.g. to remove a footer that has been processed"""
        self._end -= amount

    def reset(self) -> None:
        """Reset and recycle the buffer as empty, keeps gc out of the loop"""
        self._start = self._end = self._initial_start


#===== READERS AND WRITERS =====================================================

class FileReader:
    """Read a random access disk file, streamed or at any position"""
    def __init__(self, name:str):
        self._name = name
        self._f = None  # in case of exception
        self._f = open(name, "rb")

    def __len__(self) -> int:
        """Get the length of this disk file, in bytes"""
        ##assert self._f is not None
        here = self._f.tell()
        self._f.seek(0, 2)
        length = self._f.tell()
        self._f.seek(here)
        return length

    def __del__(self) -> None:
        """Close the file, if still open"""
        if self._f is not None:
            self._f.close()
            self._f = None

    def read(self, nbytes:int or None=None, offset:int or None=None):
        """Read the next block of data from the file"""
        ##assert self._f is not None
        if nbytes is None:
            # read to EOF
            data = self._f.read()
            if len(data) == 0:  return None  #EOF
            return data

        if offset is not None:
            p = self._f.tell()
            if p != offset:
                self._f.seek(offset)
        data = self._f.read(nbytes)
        if len(data) == 0:  return None  #EOF
        return data

class FileWriter:
    """Write a random access disk file, streamed, or at any position"""
    def __init__(self):
        self._name = None
        self._bufs  = None
        #NOTE: this 3-tuple might make a nice class abstraction
        self._blocksz = None
        self._nblocks = None
        self._lastblock = None

    def start(self, blocksz:int, nblocks:int, lastblock:int) -> None:  # exception if file too big
        """Start a buffer for a file of this size"""
        # The Pico doesn't allow large block sizes bigger than about 1K at a time,
        # so we allocate a chain of blocks that align with the receive block size
        # as that is always quite naturally small.
        assert self._name is None, "start() when already running"

        # pre-allocated buffer scheme (but copy process is slow)
        ##gc.collect()
        ##self._bufs = [bytearray(blocksz) for _ in range(nblocks)]
        ##if lastblock != 0: self._bufs.append(bytearray(lastblock))

        # allocate on demand buffer scheme (copy fast, but might get MemoryError later)
        # allocate empty slots so we can fast index later
        self._bufs = [None for _ in range(nblocks)]
        if lastblock != 0: self._bufs.append(None)

        self._blocksz = blocksz
        self._nblocks = nblocks
        self._lastblock = lastblock
        # can now use write() whenever required

    #NOTE: this should be a blockno interface really
    def write(self, data:Buffer or None, offset:int or None=None) -> None:
        """Write new data to the file"""
        if self._bufs is None:
            # this might actually happen in real life, so don't assert
            deps.message("ignoring data before META_START message, size not yet known")
        elif data is None:  # EOF
            pass  # nothing we can do, filename not known.
        elif len(data) == 0:  #NODATA
            pass  # nothing we can do, filename not known: self.snapshot()?
        else:
            blockno  = int(offset / self._blocksz)  # index into buffer chain
            residual = offset % self._blocksz
            if residual != 0:
                raise ValueError("offset alignment error %d does not align to %d" % (offset, self._blocksz))

            #PLAN-A pre-allocated buffer scheme (slow copy, but memory guaranteed)
            #src_buf   = data._buf
            #src_len   = len(data)
            #dst_buf = self._bufs[blockno]
            #dst_len = len(dst_buf)  # size of pre-allocated bytearray (lastblock might be smaller)

            #if src_len != dst_len:
            #    raise ValueError("Block size mismatch: incoming:%d store:%d" % (src_len, dst_len))
            #s = data._start  # remember there might be a header offset

            #for d in range(dst_len):
            #    dst_buf[d] = src_buf[s]
            #    s += 1

            #PLAN-B fast-copy on demand scheme (but might get MemoryError)
            #NOTE: introduce the new class Buffer(bytearray) pattern instead
            self._bufs[blockno] = data._buf[data._start:data._end]  # slice takes a copy

    def snapshot(self) -> None:
        """Save current buffer to somewhere persistent"""
        # placeholder for future work
        assert False, "UNIMPLEMENTED snapshot()"

    def get_sha256(self) -> bytes:
        """Sha256 sum the buf, for integrity checking"""
        assert self._bufs is not None, "get_sha256() with empty bufs"
        def sha256_of_buf(buf) -> bytes:
            hasher = deps.hashlib_sha256()
            for b in buf:
                hasher.update(b)  # auto adjusts to each bytearray size
            digest = hasher.digest()
            assert len(digest) == 32
            return digest
        return sha256_of_buf(self._bufs)

    def _invalidate(self):
        """Invalidate and delete any stored state"""
        self._bufs = None  # the whole buf chain will gc.collect
        gc.collect()

    def commit(self, name:str) -> None:
        """Commit current buffer to file, and cleanup"""
        assert self._bufs is not None, "commit() with empty buffs"
        f = open(name, "wb")  # exception if fails
        for buf in self._bufs:
            f.write(buf)
        f.close()
        #IDEA: could sha256 again here to make sure write worked ok?
        self._invalidate()

    def abort(self) -> None:
        """Abort the current buffer and cleanup"""
        self._invalidate()


class Link:
    # This is mostly an interface, with standard callback registration for events
    def __init__(self):
        self._reg_table = {}  # selector->[handler_fn:callable]

    def send(self, data:Buffer or None, info:dict or None=None) -> None:
        # bool: #IDEA: done or not done, tx flow control
        assert False, "Link.send needs overriding by subclass"

    def recvinto(self, user_buf: Buffer, info: dict or None = None, wait:bool=False) -> int or None:
        assert False, "Link.recvinto needs overriding by subclass"


    ##def when_received(self):  #IDEA: del=True to delete this registration
        ##pass

    ##def when_send_ready():  #IDEA: del=True to delete this registration
        ##pass

    ##def when_disconnected():  #IDEA: del=True to delete this registration
        ##pass


    def register(self, selector, handler_fn:callable or None, delete:bool=False) -> bool:
        """Register code to call, when a message arrives for a specific channel"""
        ##assert handler_fn is not None
        if not delete:
            #ADD
            if handler_fn is not None:
                if not selector in self._reg_table:
                    hlist = []
                    self._reg_table[selector] = hlist
                else:
                    hlist = self._reg_table[selector]
                    if handler_fn in hlist:
                        deps.message("warning:sel(%s) already registered, ignoring add" % str(selector))
                        return False  # NOT DONE

                hlist.append(handler_fn)
                return True  # DONE
            return False  # NOT DONE (None)
        else:
            #DELETE
            if not selector in self._reg_table:
                deps.message("warning:sel(%s) not registered, ignoring delete" % str(selector))
                return False  # NOT DONE

            hlist = self._reg_table[selector]
            if handler_fn is not None:
                # try to unregister a single function
                # this doesn't work on Pico, it sees <bound_method>
                # which probably is not comparable
                try:
                    idx = hlist.index(handler_fn)
                    hlist.pop(idx)
                    return True  # DONE
                except ValueError:
                    #NOTE: this gives a warning only on Pico (<bound_method>)
                    #I think function hashing works differently on Pico
                    ##deps.message("warning:sel(%s) not registered for(%s), ignoring delete" % (str(selector), str(handler_fn)))
                    return False  # NOT DONE

            else: # None, delete ALL registrations for this channel
                # delete all registrations for this channel
                # could be dangerous, if multiple transfers occuring!
                self._reg_table[selector] = None
                return True  # DONE, forceably!

    def dispatch(self, selector:int, data:Buffer, info:dict or None=None) -> None:
        """Dispatch args to all registered handlers"""
        hlist = self._reg_table[selector]  # KeyError if not found
        for h_fn in hlist:
            ##deps.message("dispatch %s %s to fn %s" % (str(data), str(info), str(h_fn)))
            h_fn(data, info)

class PStats:
    def __init__(self):
        self.buf_fills    = 0
        self.buf_overflow = 0
        self.prot_violate = 0
        self.all_packets  = 0
        self.trunc_events = 0
        self.trunc_bytes  = 0
        self.bad_packets  = 0
        self.junked_bytes = 0
        self.bad_plens    = 0

    def reset(self):
        self.buf_fills    = 0
        self.buf_overflow = 0
        self.prot_violate = 0
        self.all_packets  = 0
        self.trunc_events = 0
        self.trunc_bytes  = 0
        self.bad_packets  = 0
        self.junked_bytes = 0
        self.bad_plens    = 0

    def __str__(self) -> str:
        return "bfill:%d bovr:%d protv:%d allp:%d trunce:%d truncb:%d badp:%d junkb:%d badplen:%d" % (
            self.buf_fills,
            self.buf_overflow,
            self.prot_violate,
            self.all_packets,
            self.trunc_events,
            self.trunc_bytes,
            self.bad_packets,
            self.junked_bytes,
            self.bad_plens
        )

packetiser_stats = PStats()

class Packetiser(Link):
    """Transmit and receive packets, with boundary SYNC markers"""
    # mostly used for links that don't create automatic packet boundaries
    # (radios create automatic packet boundaries, UARTs and streams do not)
    _ISYNC     = 0xFF
    _IESC      = 0xFE
    _ISYNC2    = 0xFD
    _IESC2     = 0xFE
    _IESCSYNC2 = (_IESC, _ISYNC2)
    _IESCESC   = (_IESC, _IESC)

    def __init__(self, link:Link):
        Link.__init__(self)
        self._link      = link
        #NOTE: make these sizes class constants, for tuning
        self._tx_buf    = Buffer(size=512, start=0)  # no headers to peel off
        #NOTE, making this smaller than uart.rx_buf means we service uart more often
        self._rx_buf    = Buffer(size=512+32, start=0)  # no headers to peel off
        self._rx_state  = self._STATE_SYNCING
        # direct dispatch, faster
        self.send = self._send_once

    #----- SENDER --------------------------------------------------------------

    # def _send_many(self, data:Buffer or None, info:dict or None=None) -> None:
    #     """Send a packet with SYNC marks and escaped SYNCs and ESCs"""
    #     _ = info   # argused
    #     # calls send() many times. Useful for some diagnostics use-cases
    #     # Useful for UARTs that can get on with sending in parallel
    #     # Good if you don't want to create a new buffer every call
    #     if data is None:  return  # no way to send EOF here
    #
    #     self._link.send(self._tx_buf.create_from(bytes(self._ISYNC))) ##IDEA cache this
    #     for i in data:
    #         if   i == self._ISYNC: self._link.send(self._tx_buf.create_from(self._IESCSYNC2))  # escaped sync
    #         elif i == self._IESC:  self._link.send(self._tx_buf.create_from(self._IESCESC))  # stuffed esc
    #         else:                  self._link.send(self._tx_buf.create_from(i))  # data as-is
    #     # SYNC end, to prevent receiver lockup on last packet
    #     self._link.send(self._tx_buf.create_from(bytes(self._ISYNC)))  ##IDEA cache this

    def _send_once(self, user_buf:Buffer or None, info:dict or None=None) -> None:
        """Send a whole expanded packet with SYNC marks and escaped SYNCs and ESCs"""
        # calls _send() once, much faster if you can load the end buffer in one go
        _ = info  # argused
        if user_buf is None:  return  # no way to send EOF here

        b = self._tx_buf
        b.reset()

        b.append(self._ISYNC)  # start of packet
        for i in user_buf:
            if   i == self._ISYNC:  # escaped
                b.append(self._IESC)
                b.append(self._ISYNC2)
            elif i == self._IESC:   # byte stuffed
                b.append(self._IESC)
                b.append(self._IESC2)
            else:
                b.append(i)
        # SYNC end, to prevent receiver lockup on last packet
        b.append(self._ISYNC)

        self._link.send(self._tx_buf)

    #----- RECEIVER ------------------------------------------------------------
    _STATE_SYNCING    = 0
    _STATE_IN_SYNC    = 1
    _STATE_DATA       = 2
    _STATE_TRUNCATING = 3
    _STATE_TRUNCATED  = 4
    _STATE_ESCAPED    = 5
    _STATE_GOT_PACKET = 6

    @perf.tbc
    #@perf.measure("Packetiser")
    def recvinto(self, user_buf:Buffer, info:dict or None=None, wait:bool=False) -> int or None:
        _ = info  # argsused
        # don't clear user_buf here, it might have partial packet from prev call
        #NOTE: if wait is always True, we would expect user_buf to always be empty

        while True:
            if len(self._rx_buf) == 0:
                # re-fill _rx_buf
                packetiser_stats.buf_fills += 1
                ##DEPRECATE not needed if len==0 self._rx_buf.reset()
                nb = self._link.recvinto(self._rx_buf, info, wait=wait)
                ##deps.message("fillbuf:%s" % nb)

                if nb is None:  # EOF on receive link
                    # EOF means we didn't see an ending sync, so trash partial buf
                    #NOTE: need to count this as an 'interesting event'
                    deps.message("pkt:EOF(None)")
                    user_buf.reset()
                    return None  # EOF
                # might validly be partially processed data in user_buf
                # so user must pass that back in again next time to 'finish it off'
                if nb == 0:
                    assert not wait, "got nb0 when wait=True"
                    deps.message("pkt:NODATA(0)")
                    return 0  # NODATA (yet), but might be partial in rx_buf

            # process bytes in _rx_buf
            while len(self._rx_buf) > 0:
                this_byte = self._rx_buf[0]  # peek next
                ##deps.message("state:%s this_byte:%d %c" % (self._rx_state, this_byte, chr(this_byte)))

                consumed = False
                if self._rx_state == self._STATE_SYNCING:
                    # Scan for a sync byte, counting bytes that we junk
                    # If we lost sync, this is how we get back in sync
                    # which means we might need to walk over a load of junk first
                    if this_byte == self._ISYNC:
                        self._rx_state = self._STATE_IN_SYNC
                    consumed = True  # consumed

                elif self._rx_state == self._STATE_IN_SYNC:
                    # Scan for non-sync byte, used to skip valid runs of SYNC
                    if this_byte == self._ISYNC:
                        consumed = True
                    else:
                        self._rx_state = self._STATE_DATA
                        ##above: consumed = False  # must be a data byte, consume in new state

                elif self._rx_state == self._STATE_DATA:
                    # Process a data byte
                    if this_byte == self._ISYNC:
                        # this sync marks the end of the packet
                        self._rx_state = self._STATE_GOT_PACKET
                        ##above: consumed = False

                    else:
                        # must be real data
                        if user_buf.is_full():
                            # but data is too long, truncate it and resync
                            packetiser_stats.buf_overflow += 1
                            self._rx_state = self._STATE_TRUNCATING

                        # data, and will fit, check for escaping
                        elif this_byte != self._IESC:
                            # a normal data byte, just store it
                            user_buf.append(this_byte)

                        else:  # must be escaped
                            self._rx_state = self._STATE_ESCAPED
                        consumed = True

                elif self._rx_state == self._STATE_ESCAPED:
                    # Process an escaped byte
                    if this_byte == self._ISYNC:
                        # protocol violation (FE FF) but be reslient
                        packetiser_stats.prot_violate += 1
                        self._rx_state = self._STATE_TRUNCATING
                        ##above: consumed = False

                    elif user_buf.is_full():
                        packetiser_stats.buf_overflow += 1
                        self._rx_state = self._STATE_TRUNCATING
                        ##above:: consumed = False

                    else: # not full
                        if this_byte == self._ISYNC2:
                            user_buf.append(self._ISYNC)
                        elif this_byte == self._IESC2:
                            user_buf.append(self._IESC)
                        else:
                            user_buf.append(this_byte)
                        self._rx_state = self._STATE_DATA
                        consumed = True

                elif self._rx_state == self._STATE_TRUNCATING:
                    # drop bytes until we see a SYNC
                    if this_byte != self._ISYNC:
                        packetiser_stats.junked_bytes += 1
                        consumed = True
                    else:
                        self._rx_state = self._STATE_TRUNCATED
                        ##above: consumed = False  # now a sync byte, but process later

                elif self._rx_state == self._STATE_TRUNCATED:
                    user_buf.reset()  # anything in there is junk
                    self._rx_state = self._STATE_SYNCING
                    ##above: consumed = False

                elif self._rx_state == self._STATE_GOT_PACKET:
                    self._rx_state = self._STATE_SYNCING
                    packetiser_stats.all_packets += 1
                    nbytes = user_buf[0]
                    nb = len(user_buf)
                    if nbytes+1 != nb:
                        packetiser_stats.bad_plens += 1
                        #Don't use too much, it slows code down
                        deps.message("plen:%d vs [%d]" % (nbytes+1, nb))
                    return nb

                ##else:
                ##    assert False, "undefined state:%s" % str(self._rx_state)

                if consumed: self._rx_buf.ltrunc(1)

#IDEA: review this, might be unneccessary if we want to use readinto1()
#I think we want this as it provides a simple API
#but it would be better to be-a Link and provide recvinto()
class StreamReader:
    """Read a non-rewindable stream"""
    MAX_RX_BLOCKSIZE = 32

    def __init__(self, stream=None):
        self._stream = stream
        self._is_eof = False

    def read(self, max_len:int or None=None):
        """Read from the stream"""
        ##if isinstance(max_len, int) and max_len != 1:
        ##    raise ValueError("error: StreamReader max_len set to:%d" % max_len)
        if self._stream is None: return None  # no stream, always EOF
        if max_len is None: max_len = self.MAX_RX_BLOCKSIZE
        if self._is_eof: return None
        data = self._stream.read(max_len)
        ##assert isinstance(data, bytes), "need a bytes from _stream.read, got:%s" % str(type(data))
        if len(data) != max_len: self._is_eof = True  #NOTE: not the case if using buffer.read1()
        if len(data) == 0:  # always the case, for any type of read
            self._is_eof = True
            return None  # EOF
        return data

#IDEA: review this, might be unnecessary?
#I think we want this as it provides a simple API
#but it would be better to be-a Link and provide send()
class StreamWriter:
    """Write a non-rewindable stream"""
    def __init__(self, stream=None):
        self._stream = stream

    def write(self, data:Buffer) -> None:
        """Write to the stream"""
        ##assert isinstance(data, Buffer), "got:%s" % str(type(data))
        if self._stream is None: return  # no stream, do nothing
        if data is None: return
        if isinstance(data, str): data = data.encode()
        self._stream.write(data)  # takes a str
        self._stream.flush()  # force right to OS

class HexStreamReader(StreamReader):
    """Read and parse hexascii data from a non-rewindable stream"""
    def __init__(self, *args, **kwargs):
        StreamReader.__init__(self, *args, **kwargs)
        self._is_eof = False

    def read(self, max_len:int or None = None):
        """Read from the stream and decode hex to binary"""
        if max_len is None: max_len = StreamReader.MAX_RX_BLOCKSIZE
        if self._is_eof: return None
        line = StreamReader.read(self, max_len*3)  # conservative guess of max
        if line is None:
            self._is_eof = True
            return None # EOF
        if len(line) < max_len:  self._is_eof = True

        bin_data = hex_to_bin(deps.bytes_to_str(line))
        return bin_data

class HexStreamWriter(StreamWriter):
    """Write hexascii data to a non-rewindable stream"""
    def __init__(self, *args, **kwargs):
        StreamWriter.__init__(self, *args, **kwargs)

    #NOTE: Buffer?
    def write(self, data) -> None:
        """Encode data as hexascii and write to the stream"""
        if isinstance(data, str): data = data.encode()
        data = bin_to_hex(data) + '\n'
        data = data.encode()
        self._stream.write(data)


#===== LINK LAYER ==============================================================

class LinkMessage:
    PROTOCOL_OVERHEAD = 1 + 1 + 1 + 2 + 2  # len, seqno, chn, blockno16, crc16
    # link header is:
    # U8 nbytes   (not including length byte)
    # U8 seqno    (of the global link)
    # U8 chn      (identifies channel of what comes next)
    # U16 blockno
    # U8 data[]   (may be zero length)
    # U16BE crc   CCITT CRC16

    DCH    = 0x00  # OR into a channelid to get a data channel
    CCH    = 0x80  # OR into a channelid to get a control channel
    LINKCH = 0x00  # The single, always available, link channel
    # channels 0x01..0x7F are for user data
    # 0x80 = LINKCCH control channel for global link channel
    # 0x81..0xFF control channels for user channels

    # link control channel sub types
    CCH_END = 0xFF  # <nodata>

    # info keys
    CHANNEL = "chn"

    @staticmethod
    def is_eof(channel:int, data) -> bool:
        """Detect a special LINK CCH EOF message"""
        if channel is None: return False
        if channel & LinkMessage.CCH != 0:
            # control channel
            if len(data) > 0:
                # there is control data
                typeno = data[0]
                if typeno == LinkMessage.CCH_END:
                    return True  # is EOF
        return False  # is not EOF

class LinkSender(Link):
    """Send a message via the link channel protocol (protocol headers, seqno, crc etc)"""
    PROTOCOL_OVERHEAD = LinkMessage.PROTOCOL_OVERHEAD
    END_MSG = bytes([LinkMessage.CCH_END])

    def __init__(self, link:Link):
        Link.__init__(self)
        self._link = link
        self._next_seqno = 0
        self._error = None

    def get_seqno(self) -> int:
        """Get the next transmit seqno modulus value"""
        return self._next_seqno

    def send(self, data:Buffer, info:dict or None=None) -> None:
        """Send _data_ via data channel, or EOF condition via control channel"""
        ##assert data is None or isinstance(data, Buffer), "got:%s" % str(type(data))
        assert info is not None  # must have a LinkMessage.CHANNEL
        channel = info[LinkMessage.CHANNEL]
        if "blockno" in info: blockno = info["blockno"]
        else: blockno = 0

        if channel & LinkMessage.CCH != 0:
            # control channel
            self.add_header_and_send(data, channel)
        else:
            # it's a data message, but handle EOF via a control message
            if data is not None:
                self.add_header_and_send(data, LinkMessage.DCH | channel, blockno)
            else:
                buf = Buffer(self.END_MSG)
                ##deps.message("SENDING EOF PACKET")
                self.add_header_and_send(buf, LinkMessage.CCH | channel, blockno)
                ##assert False, "SENT EOF PACKET"
                del buf

    def add_header_and_send(self, data:Buffer, channel:int=LinkMessage.LINKCH, blockno:int=0) -> None:
        """Wrap and send any data to any channel"""
        # length byte not included in length byte
        lenbyte = len(data) + (self.PROTOCOL_OVERHEAD-1)
        if lenbyte > 255:
            deps.message("error:data too long, got len:%d" % lenbyte)
            return

        # HEADER len, seqno, channel, blockno(u16)
        data.prepend((lenbyte, self._next_seqno, channel, (blockno & 0xFF00)>>8, (blockno & 0xFF) ))

        # CRC
        crc = crc16(data)

        # network byte order, big-endian
        data.extend((high(crc), low(crc)))

        # advance seqno modulo 256; do last, in case of exception earlier
        self._next_seqno = (self._next_seqno + 1) & 0xFF

        # send it
        return self._link.send(data)

class LinkSenderFor(Link):
    def __init__(self, link_sender:LinkSender, channel:int):
        Link.__init__(self)
        self._link_sender = link_sender
        self._channel = channel

    def send(self, data:Buffer, info:dict or None=None) -> None:
        ##assert data is None or isinstance(data, Buffer), "got:%s" % str(type(data))
        if info is None: info = {LinkMessage.CHANNEL: self._channel}
        else:            info[LinkMessage.CHANNEL] = self._channel
        self._link_sender.send(data, info)

class LStats:
    def __init__(self):
        self._total = 0
        self._badlen = 0
        self._shorthdr = 0
        self._long = 0
        self._seqno = 0
        self._crc = 0

    def __str__(self) -> str:
        return "total:%d badlen:%d shorthdr:%d long:%d seqno:%d crc:%d" % (
            self._total,
            self._badlen,
            self._shorthdr,
            self._long,
            self._seqno,
            self._crc)

link_stats = LStats()

class LinkReceiver(Link):
    """Adds message sequence number handling, crc checking, to received data"""
    # Eventually this will handle all channels
    PROTOCOL_OVERHEAD = LinkMessage.PROTOCOL_OVERHEAD

    def __init__(self, link:Link):
        Link.__init__(self)
        self._next_seqno = 0
        self._link = link

    def get_seqno(self) -> int:
        """Get the next expected receive sequence number"""
        return self._next_seqno

    def recvinto_for(self, buf:Buffer, info:dict or None=None, channel:int or None=None, wait:bool=False) -> int or None:
        """Receive a message for a specific channel (or pump via mux to channel handler)"""
        # if there is a message and it is not for us, pump it via mux to handler,
        # so we don't have to queue incoming messages and so they don't get lost.
        if info is None: info = {LinkMessage.CHANNEL: channel}
        else:            info[LinkMessage.CHANNEL] = channel
        nb = self.recvinto(buf, info, wait=wait)
        if nb is None: return None  #EOF
        if nb == 0:    return 0     #NODATA

        # dispatch to any callback handlers first (includes EOF(None) data signalling)
        # also includes dispatching to clients other than the calling client
        self.mux_received(buf, info)
        if LinkMessage.CHANNEL in info: actual_chn = info[LinkMessage.CHANNEL]
        else:                           actual_chn = None  # channels not in use

        # now do anything that this client wants
        if nb is None:                                        return None  # EOF
        if LinkMessage.is_eof(actual_chn, buf):               return None  # EOF
        if channel is None:                                   return nb    # all messages wanted
        if actual_chn is not None and channel == actual_chn:  return nb    # it is our channel
        return 0  #NODATA (for this caller)

    def recvinto(self, buf:Buffer, info:dict or None=None, wait:bool=False) -> int or None:
        """Receive the next valid link message, separate out data and header"""
        nb = self.get_next_packet_into(buf, info, wait=wait)
        if nb is None:  return None  #EOF (CONNECTION_CLOSED)
        if nb == 0:     return 0     #NODATA

        # remove headers and footers
        HBYTES = 5 # nbytes, seqno, chn, blockno(u16)
        FBYTES = 2 # crc(16)
        buf.ltrunc(HBYTES)
        buf.rtrunc(FBYTES)
        return len(buf)

    def get_next_packet_into(self, buf:Buffer, info:dict or None=None, wait:bool=False) -> int or None:
        """Receive and validate a link layer message (but don't fully decode)"""
        nb = self._link.recvinto(buf, info, wait=wait)
        if nb is None:  return None  # EOF (e.g. CONNECTION_CLOSED)
        if nb == 0:     return 0     # NODATA

        link_stats._total += 1
        # validate length enough for a header
        if len(buf) < self.PROTOCOL_OVERHEAD:
            link_stats._shorthdr += 1
            buf.reset()  # junk any data that was captured
            return 0  #NODATA

        # validate length byte against actual packet size
        nbytes = buf[0]
        if nbytes+1 < len(buf):
            link_stats._badlen += 1
            buf.reset()  # junk any data that was captured
            return 0  #NODATA

        if nbytes+1 > len(buf):
            link_stats._long += 1
            ##deps.message("length mismatch, lbyte:%d buflen:%d" % (nbytes, len(buf)))
            buf.reset()  # junk any data that was captured
            return 0  #NODATA

        # read in the header, but validate it later when CRC is known
        nbytes = buf[0]
        seqno  = buf[1]
        chn    = buf[2]
        blockno = (buf[3] << 8) | buf[4]

        if info is not None:
            info[LinkMessage.CHANNEL] = chn
            info["blockno"] = blockno

        crc = crc16(buf, length=len(buf)-2)  # all except CRC16 bytes at end

        # read in CRC from end (remember nbytes is one less than packet size)
        rx_crc = (buf[nbytes-1] <<8) | buf[nbytes]

        # validate CRC first, so we know packet isn't damaged
        if rx_crc != crc:
            link_stats._crc += 1
            buf.reset()  # junk any data that was captured
            return 0  #NODATA

        # validate seqno
        if seqno != self._next_seqno:
            link_stats._seqno += 1
            # but keep going, it is just a warning, we will resync

        # advance seqno for valid packet, modulo 256
        self._next_seqno = (seqno+1) & 0xFF  # resync if neccessary
        return len(buf)  #NOTE, headers still intact at this stage

    #NOTE: this currently muxes ctrl and data together, probably fine if
    #different handlers are registered at point of create
    #the only selector here is channel, the rest of the muxing
    #is standard dispatch work - refactor that into the base Link class
    #and just have a mux_received() that gets the selector and delegates
    #to self.dispatch(selector, data,  info)

    def mux_received(self, buf:Buffer, info:dict or None=None) -> bool:
        """Route received (yet to be handled) data via the registration table"""
        #NOTE: unwrapping/selecting that is specific to a LinkReceiver
        if info is not None:
            if not LinkMessage.CHANNEL in info: return False
            channel = info[LinkMessage.CHANNEL]
        else:
            return False  # can't filter on channel, so ignore it

        #NOTE: refactor into Link.dispatch, generic dispatch stuff here
        if channel in self._reg_table:
            # registered
            self.dispatch(channel, buf, info)
            return True  # HANDLED
        else:
            # not registered
            return False  # NOT HANDLED

class LinkReceiverFor(Link):
    def __init__(self, link_receiver:LinkReceiver, channel:int):
        Link.__init__(self)
        self._link_receiver = link_receiver
        self._channel = channel

    def recvinto(self, buf:Buffer, info:dict or None=None, wait:bool=False) -> int or None:
        """Receive for self._channel only"""
        return self._link_receiver.recvinto_for(buf, info, self._channel, wait=wait)

class LinkManager(Link):
    """A link that can send and receive data over multiplexed channels"""
    #NOTE: This allows link-turnaround semantics and better tx/rx scheduling
    def __init__(self, link:Link):
        Link.__init__(self)
        self._linksender   = LinkSender(link)
        self._linkreceiver = LinkReceiver(link)

        # fast dispatch
        self.send = self._linksender.send
        self.recvinto = self._linkreceiver.recvinto

    #temporary
    def get_sender(self) -> LinkSender:
        return self._linksender

    #temporary
    def get_receiver(self) -> LinkReceiver:
        return self._linkreceiver


#===== GENERIC TRANSFER AGENT ==================================================

class TransferStats:
    """Keep simple statistics about data transfer"""
    def __init__(self):
        self._start_time = deps.time_time()
        self.time_used  = 0
        self.nblocks    = 0
        self.nbytes     = 0
        self.bps        = 0
        self.pps        = 0

    def update(self, nbytes:int) -> None:
        self.nblocks += 1
        self.nbytes += nbytes
        self.time_used = deps.time_time() - self._start_time
        if self.time_used > 0:
            self.bps = self.nbytes / self.time_used
            self.pps = self.nblocks / self.time_used

    def __str__(self) -> str:
        return "T:%d blk:%d by:%d PPS:%d BPS:%d" % (
            self.time_used, self.nblocks, self.nbytes, self.pps, self.bps)


class Sender:
    """Will send anything that it reads from the reader() callback via send() callback"""
    # This is the base of all senders, it can send anything that offers a reader() fn,
    # including byte arrays from sensors, and files in the filing system.

    def __init__(self, reader_fn:callable, link:Link, progress_fn:callable or None=None,
                 blocksz:int=16, repeats:int=0):
        self._reader_fn = reader_fn
        self._link = link
        self._buf = Buffer()

        self._progress_fn = progress_fn
        self._blocksz = blocksz
        self._blockno = 0
        self._repeats = repeats  # number of times to re-send same message
        self._block_counters = []
        self._stats = TransferStats()
        if progress_fn: progress_fn()  # starting #IDEA: move to send() based on state
        self._is_running = True
        self._last_stats = deps.time_time()

    def tick(self) -> bool:
        """Pump regular send processing"""
        if self._is_running:
            self.do_send_next_block()
            if not self._is_running:
                self.done()  # show final transfer status and stats
        return self._is_running

    def run(self) -> None:
        """Run to completion"""
        while self.tick(): pass

    #IDEA: could this be delegated to the block manager as an algo?
    def choose_next_block(self) -> tuple: # of (blockno:int, repno:int)
        """A place to slot in a block chooser/repeater algorithm"""
        #NOTE: This is the core feature that enables error correction at receiver
        #NOTE: returning None will cause a sequential single send of the file
        blockno = self._blockno

        # dynamically extend our block counter array
        while blockno >= len(self._block_counters):
            self._block_counters.append(0)

        # repeat current block, until the repeat limit has been reached
        repno = self._block_counters[blockno]
        self._block_counters[blockno] += 1

        # then advance to the next block
        if repno >= self._repeats:
            self._blockno += 1

        return blockno, repno

    def do_send_next_block(self) -> None:
        """Send the next block of data, if any is available"""
        ##assert self._is_running

        # READ
        #NOTE: FileReader could usefully readinto() the Buffer
        blockno, repno = self.choose_next_block()
        if blockno is not None:
            offset = self._blocksz * blockno
            data = self._reader_fn(self._blocksz, offset)
        else:
            data = self._reader_fn(self._blocksz)

        # SEND (EOF)
        if data is None:  # EOF
            #NOTE: this means the last block is only sent once, even if repeats?
            #IDEA: better to change a transfer state machine
            #do this in tick like we do with META?
            #or move END entirely to sending a control message,
            #not a data message, as other end processes those for us
            self._is_running = False
            # force an EOF packet to be sent for this file
            self._link.send(None)  # EOF
            return

        # SEND (NODATA)
        len_data = len(data)
        if len_data == 0: return  # no data available
        #NOTE: END introduce Buffer to FileReader

        self._buf.extend(data)
        del data  # prevent accidental use

        info = {"blockno": blockno}
        self._link.send(self._buf, info)

        self._buf.reset()

        self._stats.update(len_data)
        if self._progress_fn:
            # Throttled update rate
            now = deps.time_time()
            if now-self._last_stats >= 1:
                self.print_stats()
                self._last_stats = now

    @staticmethod
    def get_percent() -> int or None:
        return None

    def done(self) -> None:
        """End-effects, just print final send stats"""
        if self._progress_fn:
            self._progress_fn()  # clear current line
            self._progress_fn("\n")  # start a new line
            self._progress_fn(str(self._stats))

    def print_stats(self) -> None:
        """If progress is enabled, print stats to it"""
        if self._progress_fn:
            self._progress_fn(str(self._stats), value=self.get_percent())

class Receiver:
    """Will receive anything from the recvinto callback and write via the writer() callback"""
    # This is the base of all receivers, it can receive anything that offers a recvinto() fn,
    # and route it to anything that has a writer() callback, including screen displays,
    # actuators, and disk files.

    _STATE_STARTING      = 0
    _STATE_TRANSFERRING  = 1
    _STATE_FINISHING     = 2
    _STATE_FINISHED_OK   = 3
    _STATE_FINISHED_ERR  = 4

    def __init__(self, link:Link, writer_fn:callable, progress_fn:callable or None=None):
        self._link      = link
        self._writer_fn = writer_fn
        self._buf       = Buffer()

        self._progress_fn = progress_fn
        self._blocksz = None  # not blocked, or not yet known
        self._stats = TransferStats()
        self._crc_errs = None # don't display if there are none
        self._blockmap = None  # block map size not yet known
        if progress_fn: progress_fn()  # starting #IDEA: move to transfer function based on state
        self._last_stats = deps.time_time()
        self._state = self._STATE_STARTING
        self._is_running = True

    def set_block_info(self, blocksz:int, nblocks:int, lastblock:int) -> None:
        nb = nblocks
        if lastblock != 0: nb += 1
        self._blockmap = BitSet(nb)
        ##assert self._state == self.STATE_STARTING, "unexpected state:%s" % str(self._state)
        self._blocksz = blocksz
        self._state = self._STATE_TRANSFERRING

    def tick(self) -> bool:
        """Pump regular receive processing"""
        if self._is_running:
            self.do_next_recv(wait=True)
            if self._state == self._STATE_FINISHING:
                self.end_transfer()
                self._is_running = False

            elif self._state in (self._STATE_FINISHED_ERR, self._STATE_FINISHED_OK):
                self._is_running = False  # stop the task

        return self._is_running

    def run(self) -> None:
        """Run task to completion"""
        while self.tick(): pass

    def do_next_recv(self, info:dict or None=None, wait:bool=False) -> None:
        """Poll for a receive message, and process it if it is there"""
        ##assert self._is_running, "data receive attempted when Receiver not running"

        if info is None: info = {}  # we get back: chn, [blockno]
        nb = self._link.recvinto(self._buf, info, wait=wait)
        if nb is not None and nb != 0:
            self.process_received(self._buf, info)
        self._buf.reset()

    def process_received(self, data:Buffer, info:dict) -> None:
        """Common handling for data received, from poll or callback"""
        if self._blockmap is not None:
            # we have received the metadata
            if "blockno" in info:
                blockno = info["blockno"]
                if not self._blockmap[blockno]:
                    # this is a block we haven't seen before
                    # only write a block if we just ticked it off as received
                    # this prevents multi-writes to the file for block repeats
                    self._blockmap[blockno] = True  # this block received
                    if self._writer_fn is None:  # parent might have closed it
                        # might actually be EOF message
                        if data is not None:
                            self.data_after_close(data)
                    else:
                        self.commit_data(data, info)

                    if self._blockmap.is_complete():
                        self._state = self._STATE_FINISHING

        if data is None:  # EOF ON LINK
            self._state = self._STATE_FINISHING

    def commit_data(self, data:Buffer, info:dict) -> None:
        """Commit data to the writer"""
        ##assert isinstance(data, Buffer), "got:%s" % str(type(data))
        if data is None:  # EOF
            self._writer_fn(data)  # pass EOF down the pipeline
            return

        if len(data) == 0:
            self._writer_fn(data)  # pass NODATA down the pipeline
            return  #  no data available

        if self._blocksz is not None and "blockno" in info:
            # we now know we are blocked, and we have a blockno in payload
            offset = info["blockno"] * self._blocksz
            # so write to a specific offset
            self._writer_fn(data, offset=offset)
        else:
            # either not blocked transfer (yet), and/or no blockno in payload
            # so just keep appending to end
            self._writer_fn(data)

        # account for new received data
        self._stats.update(len(data))
        if self._progress_fn:
            # throttle the update rate
            now = deps.time_time()
            if now - self._last_stats >= 1:
                self.print_stats()
                self._last_stats = now

    @staticmethod
    def data_after_close(data:Buffer) -> None:
        """Handle any data that arrives after link is closed"""
        ##assert isinstance(data, Buffer), "got:%s" % str(type(data))
        _ = data  # argused
        deps.message("warning:new data arrived after writer closed")

    def get_percent(self) -> int or None:
        if self._blockmap is not None:
            return self._blockmap.get_percent()
        else:
            return None

    def print_stats(self) -> None:
        """If progress enabled, print stats to it"""
        if self._progress_fn:
            self._progress_fn(str(self._stats), value=self.get_percent())

    def end_transfer(self) -> None:
        """Called when a transfer ends, can be overriden for other checks or state changes"""
        self.finished_ok("Receiver ends transfer, all done")
        #NOTE, sub class can change to _STATE_FINISHING if it wants to
        #trigger end effects in the tick later.

    def finished_err(self, msg:str or None=None) -> None:
        if msg is not None: deps.message("finished_err:%s" % msg)
        self._state = self._STATE_FINISHED_ERR

    def finished_ok(self, msg:str or None=None) -> None:
        """Handle any end-effects, just print final stats"""
        if self._progress_fn:
            self._progress_fn()  # clear current line
            self._progress_fn("\n")  # start a new line
            self._progress_fn(str(self._stats))
        if msg is not None: deps.message("finished_ok:%s" % msg)
        self._state = self._STATE_FINISHED_OK
        #IDEA: do this in the app
        deps.message("final rx stats:%s" % str(self._stats))

#===== FILE TRANSFER AGENT =====================================================

TYPENO_META = 0x01  # CCH typeno for msg_start
# note, END message is FF, already known by the Message/Link

class FileSender(Sender):
    """Send something we know to be a disk file"""
    START_META   = 1     #8   # first 8 blocks are metadata message
    META_EVERY_N = 2000  #20  # send a new metadata message every N blocks
    NUM_REPEATS  = 0     #3   # number of times to re-send the same block (0 means just send once)
    # If you want to send sensor data, use a Sender() directly

    def __init__(self, filename:str, link_manager:LinkManager, progress_fn:callable or None=None,
                 blocksz:int=16, repeats:int=NUM_REPEATS):
        self._filename    = filename
        self._file_reader = FileReader(filename)
        self._linksender  = link_manager.get_sender()
        self._cch         = LinkMessage.CCH | LinkMessage.LINKCH
        self._dch         = LinkMessage.DCH | LinkMessage.LINKCH
        #NOTE: pass the file_reader and make it call read(), allows expansion later
        Sender.__init__(self, self._file_reader.read, LinkSenderFor(self._linksender, self._dch), progress_fn,
                        blocksz, repeats=repeats)

        # capture metadata of file, for later
        sz, sha256 = get_file_info(filename)
        self._filesize = sz
        self._filesha256  = sha256
        self._meta_msg = self.make_meta_msg()
        deps.message("tx:%s\nsize:%d\nsha256:%s\n" % (filename, sz, hashstr(sha256)))

        self._tickno     = 0

    def make_meta_msg(self):
        """Calculate and build a metadata message for this file"""
        ##assert self._blocksz <= 255, "make_meta_msg: block size too big, max:255, got:%d" % self._blocksz

        just_filename = deps.os_path_basename(self._filename)
        msg = bytearray()
        msg.append(TYPENO_META)

        # U16 nblocks
        nblocks = int(self._filesize / self._blocksz)
        msg.append(high(nblocks))
        msg.append(low(nblocks))

        # U8 blocksize
        msg.append(self._blocksz)

        # U8 lastblock
        lastblock = int(self._filesize % self._blocksz)
        msg.append(lastblock)

        # sha256 digest of file
        msg.extend(self._filesha256)

        # filename, z-terminated
        for ch in just_filename: msg.append(ord(ch))
        msg.append(0x00)  # terminate string, in case more data follows

        return msg

    def send_meta(self) -> None:
        """Send the cached meta message for this file"""
        ##deps.message("sending META")

        buf = Buffer()  #IDEA: keep a buffer handy for this, or use our self._buffer
        buf.extend(self._meta_msg)
        self._linksender.send(buf, {LinkMessage.CHANNEL: self._cch})  #IDEA: consider kwargs
        del buf

    def tick(self) -> bool:
        """Pump regular send processing"""
        # send the metadata every few blocks as well
        if self._tickno < self.START_META or self._tickno % self.META_EVERY_N == 0:
            self.send_meta()
            res = True
        else:
            # a normal data transfer from Sender() parent
            res = super().tick()  # calls the inner tx pipeline for us
        self._tickno += 1
        return res


class FileReceiver(Receiver):
    """Receive something we know to be a disk file"""
    #NOTE: If you want to receive sensor data, use a Receiver() directly

    def __init__(self, link_manager:LinkManager, filename:str or None, progress_fn:callable or None=None):
        # No metadata received yet
        self._local_filename = filename # might be None
        self._nblocks        = None
        self._blocksize      = None
        self._lastblock      = None
        self._sha256         = None

        # setup link connection
        self._linkreceiver   = link_manager.get_receiver()
        self._cch            = LinkMessage.CCH | LinkMessage.LINKCH
        self._dch            = LinkMessage.DCH | LinkMessage.LINKCH
        self._writer         = FileWriter()
        self._linkreceiver.register(self._cch, self.received_ctrl)  # for META_MSG, END_MSG
        Receiver.__init__(self, LinkReceiverFor(self._linkreceiver, self._dch), self._writer.write, progress_fn)

    def received_ctrl(self, data:Buffer, info:dict or None=None) -> bool:
        """Called by mux when ctrl received for this channel"""
        _ = info  # argsused

        nbytes = len(data)
        if nbytes == 0: return False  # UNHANDLED: short message

        typeno = data[0]
        if typeno == TYPENO_META:           return self._decode_meta_msg(data)
        if typeno == LinkMessage.CCH_END:   return self._decode_end_msg(data)
        return False  # NOT HANDLED  #IDEA or None vs a printable error object?

    def _decode_meta_msg(self, data:Buffer) -> bool:
        """A META message has just been received"""
        ##assert isinstance(data, Buffer), "expected Buffer, got:%s" % str(type(data))
        ##deps.message("FileReceiver:_meta_msg %s" % hexstr(data))
        if len(data) < 5+32:  # block header + meta record
            deps.message("warning:short START message, ignoring: %s" % hexstr(data))
            return False  # SHORT START

        #check what byte 0 is? It's the type byte, previously selected?
        nblocks      = (data[1]<<8) | data[2]
        blocksz      = data[3]
        lastblock    = data[4]
        sha256       = bytes(data.get_slice(5, 32))
        filename_raw = data.get_slice(5+32, len(data)-(32+5))
        filename     = deps.decode_to_str(filename_raw)
        filename     = deps.os_path_basename(filename)  # no directories allowed

        if self._nblocks is None:
            ##deps.message("capturing metadata for file")
            # first START message with metadata in it
            # capture the metadata
            self._nblocks          = nblocks
            self._blocksize        = blocksz
            self._lastblock        = lastblock
            self._sha256           = sha256
            self._remote_filename  = filename

            # now able to monitor the progress of block transfer
            self.set_block_info(blocksz, nblocks, lastblock)
            ##filesize = (nblocks * blocksz) + lastblock
            self._writer.start(blocksz, nblocks, lastblock)  #NOTE: this 3-tuple might make a nice class
            deps.message("rx:start: nb:%d bsz:%d lb:%d sha256:%s nm:%s" % (nblocks, blocksz, lastblock, hashstr(sha256), filename))

        else:
            # duplicate metadata, check it all matches
            if  nblocks != self._nblocks or \
                blocksz != self._blocksize or \
                lastblock != self._lastblock or \
                sha256 != self._sha256 or \
                filename != self._remote_filename:
                deps.message("warning:duplicate metadata received, but DIFFERENT!")
                return False  # NOT HANDLED  IDEA: might stop transfer?

        return True  # HANDLED

    def _decode_end_msg(self, data:Buffer) -> bool:
        """An END message has just been received"""
        ##assert isinstance(data, Buffer), "got:%s" % str(type(data))
        ##deps.message("FileReceiver:end_msg %s" % hexstr(data))
        _ = data  # argused

        if  self._nblocks         is not None and \
            self._blocksize       is not None and \
            self._lastblock       is not None and \
            self._sha256          is not None and \
            self._remote_filename is not None:
            # process the end-event consistently, to make sure last-block handled
            # in the recvinto correctly
            self._state = self._STATE_FINISHING

            return True  # HANDLED

        return False  # NOT HANDLED

    # called by: _end_msg()
    # also can be called by end effects due to _STATE_FINISHING
    def end_transfer(self) -> None:
        """Overrides parent, for special integrity check"""
        # deregister for callbacks, so we don't get future repeats past the end
        self._linkreceiver.register(self._cch, self.received_ctrl, delete=True)

        if self._nblocks is not None:
            if not self.check_integrity():
                # we only integrity check if metadata was received
                self.finished_err("files differ")  #  in parent
                self._writer.abort()
                ##self._writer = None  # don't do this, it will make re-runs fail
                return  # FAILED
        else:
            deps.message("warning:no blocks metadata received, can't check sha/size integrity in end_transfer")

        # else PASSED or DONT KNOW
        self._nblocks = None
        self._blocksize = None
        self._lastblock = None
        self._sha256 = None

        self._writer.commit(self._local_filename)
        ##self._writer = None  # don't do this, it will make re-runs fail

        # rename last, in case of file system error
        self.finished_ok("files identical:%s" % self._local_filename)

    def check_integrity(self) -> bool:
        """Check the integrity of the transfer file (size and sha256)"""
        ##assert self._nblocks is not None, "no metadata, can't check integrity"
        expected_sha256 = self._sha256
        # validate sha256 against received data
        actual_sha256 = self._writer.get_sha256()
        ##deps.message("rx:%s size:%d sha256:%s\n" % (self._remote_filename, actual_sz, hexstr(actual_sha256)))

        # check if the received file is intact or not
        if expected_sha256 != actual_sha256:
            # FAILED
            deps.message("error:file transfer damaged")
            if expected_sha256 != actual_sha256:
                deps.message("  sender   sha256:%s" % hexstr(expected_sha256))
                deps.message("  receiver sha256:%s" % hexstr(actual_sha256))
            return False  # INTEGRITY CHECK FAILED
        return True  # INTEGRITY CHECK PASSED

#----- USEFUL PHY LINKS --------------------------------------------------------

class InMemoryRadio:
    """Transfers data via an in-memory buffer"""
    MTU = 64  #NOTE: if set to None, no MTU is enforced

    def __init__(self):
        self._waiting = None

    def send(self, data:Buffer or None) -> bool:
        if self._waiting is not None: deps.message("warning: InMemoryRadio.send BUSY")
        # just keep going, to see if we can recover

        # copy the bytes over, because the buffer will be reset by the sender
        data.read_with(self._write)
        return True  # queued for transmit

    def _write(self, values:bytes) -> None:
        self._waiting = values

    def recvinto(self, buf:Buffer, info:dict or None=None, wait:bool=False) -> int or None:
        _ = info  # argused
        _ = wait  # argused
        if self._waiting is None:
            #NOTE: wait=True is not supported, just ignore it
            return 0  #NODATA
        packet = self._waiting
        self._waiting = None
        buf.reset()
        # copy the bytes over, as our receive Buffer is independent
        buf.extend(packet)
        return len(packet)

import sys

class StdStreamLink(Link):
    """Transfers data via a std stream"""
    MTU = None

    def __init__(self):
        Link.__init__(self)
        self._write    = sys.stdout.buffer.write
        self._readinto = sys.stdin.buffer.readinto1  # can terminate early

    def send(self, data:Buffer or None, info:dict or None=None) -> None:
        data.read_with(self._write)

    def recvinto(self, buf:Buffer, info:dict or None=None, wait:bool=False) -> int or None:
        return buf.write_with(self._readinto)

#NOTE: this might just be a Packetiser.wrap(StdStreamLink())
class StdStreamRadio(Link):
    """A packetised version of std streams"""
    #NOTE: no need for a MTU on a stream really, so largest is
    #1 + (255*2) due to how FE & FF expand to 2 bytes with packetiser
    #and all our protocols use a single length byte
    MTU = 1 + (255*2)  #if set to None, no MTU is enforced

    def __init__(self):
        Link.__init__(self)
        self._packetiser = Packetiser(StdStreamLink())

        # direct dispatch (fast)
        self.send     = self._packetiser.send
        self.recvinto = self._packetiser.recvinto
# END: dttk.py
