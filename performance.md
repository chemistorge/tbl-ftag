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


# 15/02/2023: memoryview() and rewritting the Buffer abstraction

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
the stack. This removes the overhead associated with cop

Adam Dunkels Lightweight IP (LwIP) uses a protobuf scheme, whereby pbufs
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

## The Python Buffer Protocol

After a lot of reading Python docs and little experiments at the REPL prompt,
it because clear that the best thing to do is to try to get Python to always
use a thing called the 'Buffer Protocol'. This is a C-side API that you
can't access directly in Python, but if you make the right choices in your
design, you can force Python to make good use of it.

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

## Slices of data

Yes Yes, but the real problem here to solve, was to provide fast read, write,
and copy access to limited ranges of a bytearray (inside my ```Buffer()``` object).
How can we manage the offsets and still get fast access to the internal
memory of the ```bytearray```? And how, specifically, can we write to just a
middle portion of a ```bytearray``` without Python first taking an independent
copy of that slice, as happens with ```data = ba[3:15]```?

YOU'LL HAVE TO WAIT UNTIL THE NEXT INSTALLMENT!!

## New performance measures

As a teaser, here are the new performance measures with the improved code

```
Unthrottled tx stats:
  tx transfer: T:6 blk:695 by:34710 PPS:115 BPS:5785   <<< WOW,
```

The receiver falls over with errors at that rate - but STONKING!

```
Throtted at 40 packets per second
  tx transfer: T:72 blk:2780 by:138840 PPS:38 BPS:1928
```

That's more like it!

```
Adding in resilient re-sending of data:
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



# Future Work

There is much optimisation to do to this code.  Here are some of the items
on our todo list:

* Inverting the receive pipeline from a polled architecture to a callback 
architecture. This will improve responsiveness to incoming packets, but
more importantly it will also enable the multi-session multiplex feature to
be opened up, whereby multiple concurrent transfers can work alongise each
other.

* Do a comparative study between our simple cooperative scheduling framework,
and look at whether the ```uasync``` module will be a better way to schedule
work and get it to execute in a timely and responsive way.

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






