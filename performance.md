# Performance Optimisation

This is a live document that captures our current view on optimising the
performance of this communications code. As such, it will be updated with
facts and figures and analysis as the project progresses.


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

## The Starting Point

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

## Future Work

There is much optimisation to do to this code.  Here are some of the items
on our todo list:

* Introduction of ```memoryview()``` to remove any remaining buffer slicing 
operations will make a big difference, as it takes good advantage of the Buffer 
Protocol  such that all of the key work is done in the C domain loops, rather 
than being done in MicroPython domain loops.

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






