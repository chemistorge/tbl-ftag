# Performance Optimisation

This is a live document that captures our current view on optimising the
performance of this communications code. As such, it will be updated with
facts and figures and analysis as the project progresses.

The latest change added since last version, is the section on ```memoryview()```.


## The Importance of Performance

Good performance of communications code is vital in order to get good end to end
transfer rates. Because communications code is effectively one big pipeline
from a byte in a file being sent, to a byte in a file that is received, every
microsecond that you can shave of the processing of each packet and each byte
makes a difference.

Optimising performance is quite an art, but requires a certain amount of good
common sense too - optimising a lot off of a little loop that is used 0.1% of the 
time, is less effective than shaving a little bit off of a loop that is used 50% 
of the time.

There are many ways of optimising code for better performance, and this page
aims to collect together all of the various techniques and insights captured
throughout this process.


# 08/02/2023 The Starting Point

The codebase was first completely developed in standard host Python
(CPython) 3. Specifically this version of Python 3.6 on my (old) Mac laptop:

```
Python 3.6.1 (v3.6.1:69c0db5050, Mar 21 2017, 01:21:04) 
[GCC 4.2.1 (Apple Inc. build 5666) (dot 3)] on darwin
```

The approach taken was to build a useful reusable toolkit of parts, and
then connect those together to create a file transfer agent. We didn't worry
too much about performance at this stage, we just wanted to get the design
mostly right, and get a 'working reference design' on standard Python to move
forward from.

To get the design right, we developed three test harnesses:

```test_dttk.py``` is a set of unit tests to test aspects of the various objects.

```make test_loopback``` transfers between sender and receiver in-process, via a
single memory buffer, and this aimed to push us to think about how code
can be simply run cooperatively so the sender and receiver can run together.
A key design point here was to keep it simple, avoid threads, and not use
anything that would tie this code to the host Python, but mostly to build
a tester that worked more like a radio link would (whereby packets are
formed and sent, and received as a whole packet).

```make test_pipeline``` transfers code between sender and receiver out-of-process,
via stdout and stdin - you can basically build a pipeline between sender
and receiver with a unix pipe (and the host examples show you various ways
to do that).
A key design point here was to force us to deal with packetisation boundaries,
and this is more consistent with sending data over a UART link where bytes
don't arrive in nice packet sized chunks.

The next step was to get some good measures of performance, and work out
roughly where most of the execution time was going. For that, we developed
```perf.py``` with some decorators that can be applied to functions to measure
execution time. Vital to this was realising that min and max and cumulative
times are really needed (not just cumulative execution time) as it shows
best and worst case runtimes.

We then ported this to MicroPython on the Raspberry Pi Pico and resolved the 
inevitable platform differences, and re measured everything. My my, it's
so much slower on the Pico, of course! Interpreted bytecode, and a processor
that runs at 125MHz rather than 4GHz, and a tiny amount of RAM to work with.

```perf.py``` gave some good help in shining the torchlight on key bottleknecks,
and buffer copying was a big issue at this stage. We wrote the ```Buffer()```
abstraction to attempt to remove buffer copying and the design of that 
improved things a bit, but the implementation doesn't play into MicroPython's
strengths completely (see later for more on that) and it needs re-working.

For example, early versions of the code performed really badly (even worse
than they are now!) at about 1 packet per second over a UART link.
Most of the issue is at the receiver end, with it not getting round quick
enough to receive more data, and buffers eventually swelling up and incoming
data being lost. We had to throttle the sender in order to get anything
reasonable out of the early versions of the receiver.

## MicroPython Interpretation

MicroPython in its standard form compiles to bytecode. These bytecodes are
then interpreted by an interpreter loop, which dispatches each bytecode 
instruction (and optional parameter) to the C-code that handles that bytecode.
The MicroPython interpreter is well written and quite efficient, but it can
be 10-20 times slower than the equivalent C code.

On Jan 25th, Adafruit published a short article I wrote about our 
[current project](https://blog.adafruit.com/2023/01/25/harlow-college-builds-cubesats-with-students-using-the-raspberry-pi-pico-space-raspberrypi-micropython-circuitpython-ataylorfpga-raspberry_pi-pimoroni/)

After we published this article, 
[Matty from the Melbourne MicroPython meetup](https://github.com/mattytrentini/)
got in touch, and we started to chat about performance. 
He usefully mentioned the native and viper compilers in MicroPython. 

I found 
[this page](https://docs.micropython.org/en/v1.9.3/pyboard/reference/speed_python.html) 
in particular very useful background reading (the links to the KickStarter notes 
are also vital reading).

Basically, just add the ```@micropython.viper``` decorator before your function name,
and it compiles with viper into optimised thumb machine code, using machine-word
sized variables and pointers for buffers.

So, here are some real (initial) measures:

* Without any optimisation, the ```crc16()``` algorithm took 27,032 us to run (23ms)
for a 64 byte block of data.

* With viper optimisation, it took about 700us to run the same algorithm
on the same block of data.

On the Raspberry Pi Pico, this translates to the following transfer stats:

```
SEND (unoptimised):
    <function add_header_and_send> measure: calls:772 min:5,196 max:36,134 cum:18,631,708
    transfer: T:22 blk:695 by:34710 PPS:31 BPS:1577

SEND (optimised)
    <function add_header_and_send> measure: calls:772 min:3,988 max:24,536 cum:11,925,377
    transfer: T:13 blk:695 by:34710 PPS:53 BPS:2670

RECEIVE (unoptimised)
    <function get_next_packet_into> measure: calls:257 min:35,492 max:50,283 cum:9,847,471

RECEIVE (optimised)
    <function get_next_packet_into> measure: calls:257 min:24,543 max:33,458 cum:6,980,689
```

Clearly there are many parts to a send and receive pipeline, and these figures are based
on data sent over a UART running at 115200bps. So additional end to end wait times
will affect some of the figures.


# 16/02/2023: memoryview() and rewritting the Buffer abstraction

## The Problem

The ```Buffer()``` abstraction in ```dttk.py``` was written to recognise two 
vital facts:
 
1. when sending messages with a protocol, the user data from the application
has to have some header bytes inserted at the start and a CRC at the end.

2. when receiving messages with a protocol, the incoming message has headers
and the CRC footer stripped, to generate the user payload sent up to the
application.

The real problem with this is that every time you want to add a header as
you go down the stack for a send, you have to copy the whole buffer to a new
buffer, leaving space for the new headers. On the way up the stack for a
receive, you have to copy part of the data into a new buffer to remove
headers. All this copying between buffers takes time, and is on the critical
path of data transfer, significantly increasing system loading and slowing
everything down.  The problem compounds further if there are multiple
layers of a network stack (and the OSI 7-layer model suggests a reference
stack with 7 such layers). 

## Typical Solutions

There is a well known approach to this in the industry called 'zero copy buffers',
whereby data is filled into buffers that are either chains of little parts
with headers and data and footers, or the buffer is intentionally filled in
and accessed by moving the start and end offsets as it moves up and down
the stack. This removes the overhead associated with copying data.

[Adam Dunkels Lightweight IP (LwIP)](https://en.wikipedia.org/wiki/LwIP) 
uses a protobuf scheme, whereby 
[pbufs](https://www.nongnu.org/lwip/2_1_x/structpbuf.html)
can be chained together and processed internally by the stack quite
efficiently. But the problem with this is that the stack then has to also
deal with garbage collection of buffers, and you can't just index those
buffers in the normal way, you have to access them via the pbuf abstraction.

Because the stack we are developing here runs on MicroPython, we already
know that there will be some natural garbage collection in normal operation,
and MicroPython manages that for us. So we chose to go with an offset-based
scheme, whereby a bigger buffer is allocated and an initial start offset
of 10 bytes used, to allow for header expansion as the data flows down
the stack. We wrote a ```Buffer()``` abstraction to manage this offsetting,
and went through about 3 versions to get to the stats collected earlier.
But the performance was still shoddy.


## bytes() vs bytearray()

A ```bytearray()``` is a mutable data structure that you can read and write,
contract and extend at will. A ```bytes()``` is an immutable data structure.
Some operations on a ```bytearray()``` will cause memory to expand or move,
but the memory associated with a ```bytes()``` stays current and unmodified
until the object has zero references left and it gets deleted by the 
garbage collector.

You might usefully at the REPL prompt in Python use ```dir(bytearray)```
and ```dir(bytes)``` to see some of the main differences between them.

Using a ```bytes()``` to store data is quite a good design pattern, because
of its immutability - you can pass it up and down a stack and be sure that
nothing gets accidentally changed along the way; whereas a ```bytearray()```
can be changed by any software that has a reference to it. This can produce
some really hard to find bugs, so the immutability of a ```bytes()``` forces
you to code a bit more 'functionally' where data is returned from a function,
it gets consumed by various services, and finally it disappears when it is
no longer needed.

This is actually a critical point to understand, because it is common to see
a lot of evidence of mixing of ```bytes()``` and ```bytearray()``` throughout
a codebase, with no real policy as to where one or the other is used.


## The Python Buffer Protocol

One thing that ```bytes()``` and ```bytearray()``` do have in common though,
is that they both support the 
[Python Buffer Protocol](https://docs.python.org/3/c-api/buffer.html). 
This is a C-side API that you can't access directly in Python, but if you make 
the right design choices, you can force Python to make good use of it.

The Buffer Protocol allows fast direct memory access to blocks of bytes
in the memory blocks of your data structures, all while keeping the code
running inside the C-domain. To do this, you work with ```bytes()``` and
```bytearray()``` objects, slices with ```[ ]``` operators, and two useful
objects called ```memoryview()``` and ```slice()```.

So, this is a very slow way to copy data:

```python
b = bytes(b'12345678')
ba = bytearray(20)
for i in range(len(b)):
    ba[i] = b[i]
```

The reason this is so slow, is because the loop happens as a set of python
bytecodes; thus it is interpreted, and on average 10-20 times slower than
doing this in C.

In this case, the fastest way to initiate the Buffer Protocol is this:

```python
b = bytes(b'12345678')
ba = bytearray(b)
```

The ```bytearray``` constructor will take a bytes-like object, and because
both ```bytes``` and ```bytearray``` support the Buffer Protocol, the
memory copy between b and ba happens entirely in the C-domain.

While this doesn't make much difference on a 4GHz machine, or with 8 bytes of
data, it does make a significant difference on a 125MHz Raspberry Pi Pico,
and also a significant difference if you have very large buffers.

## Avoiding copies of data

The real problem here to solve, was to provide fast read, write, and copy access 
to limited ranges of a bytearray (inside my ```Buffer()``` object).
How can we manage the offsets and still get fast access to the internal
memory of the ```bytearray```? 

Let's assume we have a 3 byte header, and a 2 byte CRC footer in an incoming
received message, and that once those are processed, we want to strip them
off and pass the inner payload data up to the application (so that it has
the correct length and contains the correct data without headers and
footers).

The following code illustrates the problem

```python
packet = bytes(b'HDR12345678CC')
payload = packet[3:-2]  # takes a copy
```

The subscript slicing provides neat and easy access to the inner payload,
but it initiates an independent copy of the data. For a small packet that
is not much overhead (and the copy happens in the C-domain due to the
Buffer Protocol), but you get an independent copy of the data, that will
eventually need to be garbage collected. In a large network stack that has
to be performant, all these little copies add up (especially as packet sizes
are increased to improve throughput), and a lot of extra garbage collection
happens. Adding significant garbage collection into the transmit or receive
pipeline eventually bites back, especially on a slow and memory constrained 
system such as those that MicroPython targets; you ultimately get a large
pause in processing, while the garbage is collected, to make way for new
objects.

## Enter memoryview(), the saviour

Python has a really useful object called a ```memoryview()``` which provides
a virtual window over any object that is bytes-like; it supports the Buffer
Protocol, and the inner object that it wraps supports the buffer protocol.

An example will help here:

```python
packet = bytes("HDR12345678CC")
mv = memoryview(packet)

packet[1]      # normal read-based indexing
mv[1]          # also works with mv
packet[3:-2]   # slice access, but takes a copy
mv[3:-2]       # slice access, but does NOT take a copy
```

The key point to note here is that ```memoryview()``` is a wrapper around
any object, it provides read (and if supported by the inner object) write
access, in a way that doesn't require the object to be copied in order to
access slices.

This is precisely what we need for our packet buffers; it means that we can
provide LHS and RHS indexes and move these indexes as the packet moves up
and down the stack, but the same underlying memory is always referenced.
When we move the LHS and RHS and access the inner data payload as a slice,
we get the same bytes, but an internal copy is not required, so there is
no inevitable garbage collection later. We can also, if required, choose
for the inner object to be immutable (```bytes()```) or mutable (```bytearray()```)
depending on the level of access we want to provide to it throughout the
application.

## Slicing, and hiding the slice

The final piece of the puzzle, is to keep track of the LHS and RHS offsets
into the packet buffer. One way might be to hold two variables, thus:

```python
packet = b'HDR12345678CC'
mv = memoryview(packet)

lhs = 0
rhs = 13
mv[lhs:rhs]  # the whole packet

# strip header
lhs = 3
mv[lhs:rhs]  # a view, no copies!

# strip CRC footer
rhs = 11
mv[lhs:rhs]  # a view, no copies!
```

It's a pain to keep the lhs and rhs variables together.
An alternative way would be to use a ```slice()``` object.
A ```slice()``` is another wrapper object that enapsulates the full address
of a start, a stop (and optionally a step) of any object. It can be used
inside the subscript operator ```[ ]``` and forms a multi-valued address.

```python
packet = b'HDR12345678CC'
mv = memoryview(packet)
view = slice(0, len(packet))
mv[view]        # the whole packet

view = slice(view.start+3, view.stop)
mv[view]        # the header is stripped

view = slice(view.start, view.stop-2)
mv[view]        # the CRC footer is also stripped

mv[:]           # the whole packet

mv[2] = 42      # make a change in the header
mv[0:3]         # just the header, modified
```

While slices are super useful as a 'fully ranged address', they are immutable;
so every time you modify the slice, you create a new object. But you can pass
them around as a sort of 'template' for an object and given them a name,
which works well for fixed sized objects with fixed sized fields in them, thus:

```python
HEADER = slice(0, 3)
BODY   = slice(3, 11)
CRC    = slice(11, 13)
packet = bytes('bHDR12345678CC')

packet[HEADER]
packet[BODY]
packet[CRC]
```

However, in our ```Buffer()``` use case, there is an even neater trick with
slices that we can use.

## __getitem__ and slice()

A class that has a ```__getitem__``` function, can be used to provide indexing
and subscripting support. The two are actually slightly different, but they
are implemented the same way.

Indexing means a single entry like: ```a[1]``` and Subscripting means a range
such as ```a[3:7]``` or ```a[3:-2]```.

An example makes this easier to understand.

```
class Packet:
    def __init__(self, data:bytes):
        self._buf = bytearray(data)
        
    def __getitem__(self, idx):
        print("index:%s" % idx)
        return self._buf[idx]
        
p = Packet(b'HDR12345678CC)
```

With this definition of packet, we can access individual bytes of the packet,
without exposing the inner ```bytearray``` to the caller:

```python
# indexing example
print(p[1])         # index:1 68 (D)
print(p[2])         # index:2 82 (R)
```

The real power of this, is that python also supports subscripting with the
```__getitem__``` method, thus:

```python
print(p[0:3])       # index:slice(0,3,None) HDR
print(p[3:11])      # index:slice(3,11,None) 12345678
print(p[HEADER])    # index:slice(0,3,None) HDR
print(p[BODY])      # index:slice(3,11,None) 12345678
```

This works, because Python passes an ```int``` for indexing,  and a
```slice()``` for subscripting. Because the inner ```bytearray``` of ```Packet```
also supports both ```int``` and ```slice``` indexing and subscripting,
this all comes out in the wash.

It is worth noting that if your inner object doesn't support subscripting
but does support indexing, you can work around that as follows:

```python
   def __getitem__(self, idx):
       if isinstance(idx, int):
           # indexing code here
       elif isinstance(idx, slice):
           # slicing code here
       else: assert False, "unexpected:%s" % str(type(idx))
```
## A neat trick to prevent unintended referencing

What is wrong with this code?

```python
packet = b'HDR12345678CC'
hdr = packet[0:3]       # a copy, of the header
body = packet[3:11]     # a copy, of the body
crc  = packet[11:]      # a copy, of the crc

whole = packet          #<<< a REFERENCE to the same object
```

Yes, that's right, the ```whole``` is not a copy of the buffer, it is a
reference to the same buffer. Sometimes this is important.

You can fix it like this:

```python
whole = packet[0:len(packet)]  # messy
whole = packet[:]              # much cleaner, uses BufferProtocol to copy
```

The same works on the LHS of an assignment, so if you are copying into a new
bytearray, the same occurs:

```python
packet = b'HDR12345678CC'
hdr = bytearray(20)
hdr = packet[0:3]           #<<< takes a copy, then assigns that to hdr
                            # original bytearray(20) is wasted

# better
hdr = bytearray(20)
hdr[0:3] = packet[0:3]      # Buffer Protocol used to copy 3 bytes into the bytearray(20)

# or even...
ten = b'1234567890'
buf = bytearray(10)
buf[:] = ten[:]             # copy 10 bytes from ten to buf
                            # will expand buf if it is too small
                            # but 'buf' is not a REFERENCE to ten, it is a copy
```

# 17 Feb 2023: The final piece: Building an encapsulated Buffer()

If you look in file [dttk.py](src/dttk.py) at the ```Buffer()``` class, you
will see the most up to date version of this code. However, to pull everything
we have learnt into one final conclusion, let's work through some of the
key techniques and look at how they surface inside the ```Buffer()```

## Typical workflow of a Buffer()

A typical usage workflow for the buffer, sees the buffer being recycled rather
than recreated on every use (this reduces garbage collection load a little, and
is a common technique used with Java to get good garbage collection performance
in highly scaleable systems).

For the send workflow:

```python
b = Buffer()                # create it, once, at program start
...
b.extend(b'DATA*HERE*')     # application puts some data in the buffer
b.prepend(b'HDR')           # a header is tacked onto the LHS
b.extend((0x3C, 0x2D))      # a CRC is tacked onto the RHS
...                         # stuff here to use/send the buffer
b.reset()                   # reset LHS RHS pointers and recycle it
```

For the receive workflow:

```python
b = Buffer()                # create it, once, at program start
...
b.write_with(uart.readinto) # zero-copy fill the buffer with data from a UART
...
b.ltrunc(3)                 # remove the header, once processed
b.rtrunc(2)                 # remove the CRC footer, once processed
file_write(b)               # write the active range/user payload to a file
...
b.reset()                   # reset the LHS and RHS pointers and recycle it
```

We'll dig into the ```write_with()``` method a little later.

## using the memoryview() on a bytearray()

To get good read and write performance with zero-copy semantics, the core
internal data structure is a ```bytearray``` wrapped with a ```memoryview```
for the 'active (used) range' of the buffer. This way it can expand and contract
without the need for any copying, providing we maintain the LHS and RHS offsets
correctly:

```python
class Buffer:
    DEFAULT_START = 10  # allow LHS space for headers
    DEFAULT_SIZE = 128

    def __init__(self, initial_value=None, size:int=DEFAULT_SIZE, start:int=DEFAULT_START):
        self._mv = memoryview(bytearray(size))
        self._start = self._end = self._initial_start = start
        self._used = self._mv[start:start]
        if initial_value is not None:
            self.extend(initial_value)
```

An initial_value can be provided, and you can adjust the overall buffer size and 
start offset. Remember, the start offset is used to allow the LHS to expand out 
along the send pipeline as headers are prepended. In this implementation,
if your initial size and offset are wrong, things break further down the
pipeline. (Note, version 2 of this class had a grow feature, but it turned out
to be more complex, and things perform better if you know by design what your
worst case buffer size and header requirements are, which you usually do
anyway).

The ```used``` is a ranged slice on the memory view. An earlier version did
use a ```slice()``` object here to maintain LHS and RHS view pointers, but
every time you change them you have to ditch it and create a new slice,
because slices are an immutable object. So the ```used``` variable basically
does the same in a cleaner way.

## Magic dunder accessors

These 4 dunder accessors provide all the magic to both index and subscript
the internal buffer, for all useful read and write use-cases:

```python
    def __setitem__(self, idx, value):
        self._used[idx] = value

    def __getitem__(self, idx):
        return self._used[idx]

    def __len__(self):
        return len(self._used)

    def __iter__(self):
        return iter(self._used)
```

Remember, that Python might pass an ```int``` or a ```slice``` as the ```idx```
parameter; because ```self._used``` is actually a sliced ```memoryview```
object, it supports all the required methods that make all this work seamlessly,
while also enforcing the LHS and RHS pointers for you. If you try to break
outside of the bounds of LHS:RHS, you get the usual ```IndexError``` exception,
as expected.

## Appending a single item

```append()``` is really a special case of ```extend()```, and an early version
of ```Buffer``` detected the type of the parameter and selected the correct operation.
However, the append/extend protocol is more compliant with other bytes-like
objects, so we split it out again:

```python
    def append(self, value:int) -> None:
        new_used = self._mv[self._start: self._end+1]  # exception if full
        length = self._end - self._start
        new_used[length] = value
        self._end += 1
        self._used = new_used
```

First, the viewed range is extended by one slot at the RHS, and this is done
first, because if your view or buffer size is exceeded, you get the usual
exception here, and no state has been updated.

Then the data is inserted, RHS updated, and it's done.

## Extending with multiple items

```extend()``` takes an iterable, so anything that generates multiple
integer values, and each of those get added to the RHS.

```python
    def extend(self, values) -> None:
        len_old_used = len(self._used)
        len_values = len(values)
        # extend the viewed range to accept the new data
        new_used = self._mv[self._start:self._end+len_values]  # exception if full

        try:
            new_used[len_old_used:len_old_used+len_values] = values
        except: #Cpython=TypeError, MicroPython=NotImplementedError
            # no it isn't, so iterate it instead
            for i in range(len_values):
                new_used[len_old_used+i] = values[i]
        # change last, in case of exception
        self._end += len_values
        self._used = new_used
```

Again, the view is extended first in case it exceeds the allowed bounds,
in which case you get the usual exception. 

The try/except block was required here because the failure modes vary between
CPython and MicroPython, they throw different exceptions. This block covers
two separate cases:

1. you have passed a ```values``` that is a bytes-like object and supports
the Python Buffer Protocol; in which case, this is a super speedy C-level copy.

2. you have passed a ```value``` that is more complex and is not a bytes-like
object (e.g. a list of integers, or a generator). In that case, values are
iterated (as it is assumed to be an iterable of int) and filled into the internal
array one value at a time.

Finally, the RHS pointer is updated and the state changed. Again, this is
done last, in case of any errors, in which case the state is not left in
an indeterminate mess.

NOTE: ```prepend1()``` and ```prepend()``` use a similar approach, but
work on the LHS.

## Truncating to remove headers and footers

Left and right truncation are mostly self explanatory and very similar:

```python    
def ltrunc(self, amount:int) -> None:
    new_used = self._mv[self._start+amount:self._end]  # exception if out of range
    self._start += amount
    self._used = new_used
```

## Buffer readinto() without exposing the internals

One final issue is to provide a size-preserving method of writing to the
internal buffer, such that internal state variables don't need to break out
from the encapsulation.

A typical use-case is reading from a UART peripheral:

```python
by = uart.read()         # creates a new bytes object
...
ba = bytearray(20)
nb = uart.readinto(ba)  # fills the byte array, returns number of bytes filled

b = Buffer()
b.write_with(uart.readinto)
```

As you can see from above, the ```UART``` object in MicroPython usefully
provides a ```readinto()``` method that will read data into a provided
bytearray (or anything that is indexable and writeable, actually).

But it returns the number of bytes written, and the internal ```memoryview``` inside
our ```Buffer``` is maintained with a ```self._end``` and a ```self._used``` pair
of variables. These variables need to be updated so that if the UART only reads
5 bytes into our 128 byte buffer, the end and used view are both correctly updated.

# Performance measures

Here are the performance stats with the new ```Buffer()``` added.

```
Unthrottled tx stats:
  tx transfer: T:6 blk:695 by:34710 PPS:115 BPS:5785   <<< Significantly faster
```

The receiver is currently not quite as performant as the transmitter; there
is more work there to do, to keep up with this faster sender, so we throttle
our sends at a level that the receiver can currently sustain:

```
Throtted at 40 packets per second
  tx transfer: T:72 blk:2780 by:138840 PPS:38 BPS:1928
```

## Adding in resilience

Now we have moved out of the '1 block per second' realm and into the '40'
blocks per second' realm, we can use that extra available time to add in some
resilience of the metadata and data records:

```
START_META   = 8   # first 8 blocks are metadata message
META_EVERY_N = 50  # send a new metadata message every N blocks
NUM_REPEATS  = 3   # number of times to re-send the same block (0 means just send once)
    
rx transfer: T:75 blk:695 by:34710 PPS:9 BPS:462    
```

So, a transfer of a 35K jpeg (our target image size) over a UART, sending
8 meta messages at the start, a meta message every 50 blocks, and repeating
each block 3 times for resilience in case of damaged payloads (4 total times
per block) transfers in a little over 1 minute. Compared to our early
experiments of 1 block per second with no repeats, that's 10 times
increase in transfer speed, with a 4 times increase in resilience.

## Final installment: viper compilation in a platform-independent way

THIS WILL BE THE SUBJECT OF THE FINAL INSTALLMENT.

# Future Work

There is much optimisation to do to this code.  Here are some of the items
on our todo list:

* Inverting the receive pipeline from a polled architecture to a callback 
architecture. This will improve responsiveness to incoming packets, but
more importantly it will also enable the multi-session multiplex feature to
be opened up, whereby multiple concurrent transfers can work alongise each
other.

* apply the viper compiler to more of the code, and find an easy way to
seamlessly switch it on and off as we move code between host python and
MicroPython

* Further optimise packet sizes based on real measurements - the ```Packetiser()```
for example receives data in large chunks, but sends it via a double buffered
scheme. UART buffer sizes and internal buffer sizes are large, but it feels
that this balance between buffer sizes and how much data is sent to the UART
in one could be optimised by informed data collection. Specifically, if you
can 'get on with' transferring some bytes on a slow link, while calculating
the next few bytes, you get the benefits of overlapped work. But if code
calls-in too often (e.g. every byte as it is generated) the additional
call-return overheads swamp execution time.

* Do a comparative study between our simple cooperative scheduling framework,
and look at whether the ```uasync``` module will be a better way to schedule
work and get it to execute in a timely and responsive way.






