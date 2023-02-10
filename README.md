# File Transfer Agent (FTAG)

## What is this?

This is a set of code libraries, written in Python, with the purpose of
building configurable file-transfer applications between different computer systems.

The code is written to work on both host-based Python systems 
(such as Mac/PC/Linux/Raspberry Pi) as well as micro-controller systems running 
MicroPython (NOTE: such as the Raspberry Pi Pico).

## Get going quick

For use on host-Python (e.g. Mac, PC, Linux, Raspberry Pi Raspbian),
please read [host_instructions.md](./host_instructions.md)

For use on a Raspberry Pi Pico running MicroPython,
please read [pico_instructions.md](./pico_instructions.md)


## What is it for?

With FTAG, you can transfer binary files stored in the filing system,
and receive those files intact on 1 or more remote systems.

FTAG is currently configured as a simplex broadcast based system, 
whereby if you transmit data via a radio link from one sender, multiple
receivers will be able to receive the data. A typical use-case for this would
be a high-altitude balloon or quadcopter based remote photography system.

The internal architecture separates the transmit and receive pipelines such
that they work independently, so it is possible to build a 1 to many broadcast
system, or even a peer-based 1 to 1 transfer system, amongst other 
configurations.

You could use an incoming data stream to receive a list of file send requests,
or you could even build a self-acknowledging retry based transfer using the
separate send and receive pipeines. The key aspect of the design is that
send and receive are independent, which allows many more different types
of transfer systems to be constructed.

There are also aspirations to send any type of data, such as telemetry data
acquired from sensors, concurrently with any number of file transfers.
(note, future work, not yet implemented).


## What does it do for me?

FTAG includes error-detection in the form of CRC protected payloads, such that
any receiver can verify the integrity of a received payload before it is 
processed.

It includes a link layer manager that has a rolling sequence number field, and
errors caused by bit-errors, byte-errors (thus crc-failures), short-packets,
long-packets, and missing packets can be detected via this sequence number
check.

FTAG supports a block-sending protocol that allows blocks of data to be sent
in-order, out-of-order, and with 0 or more repeats of the data. Each payload
contains a block number in the range of 0..65535, and there is a block sizing
system that can be used to extend the size of transferred files beyond 64KB
and to allow configuration of system performance and loading.

There is a rudimentary error-correction system, whereby blocks may be repeated
on a carousel (a bit like the old TV Teletext systems); blocks may be sent
many times, in any order, on a schedule; the receiver keeps a list of received
blocks and captures and writes only needed blocks as they arrive. Note that
this scheduled sender system also scales down well to very slow background
file transfer systems (e.g. it might scale down well to LoRa based file
transfer that takes place over a large number of days).

FTAG also performs a final integrity check of the transferred file; the 
sender takes a SHA256 hash of the whole file and sends it along with file
size and name information in a meta-message. When the receiver has received
all blocks, it verifies the SHA256 hash, and only writes the file to the
filing system when it is completely received.


## Architecture

This repository contains a number of building blocks, and FTAG is basically
a pre-configured set of demos to show one particular configuration of those
building blocks. It is hoped that others will use this toolkit in different
configurations to build systems with the features and performance 
characteristics required by their application.

## Files and their purpose

```ftag.py``` - a demo application that detects the platform being used, and 
provides some ready-rolled helper functions.

```ftag_host.py``` - a host-Python implementation that provides an 
in-process(loopback) and an out-of-process(send/receive stdstreams) method of 
testing all of the transfer algorithms.

```ftag_pico.py``` - a Raspberry Pi Pico (MicroPython) implementation that 
provides a single-system(loopback) and a multi-system(send/receive) method of 
testing all of the transfer algorithms via the integral UART. UART messages
are chunked into detectable packets using a special packetiser/de-packetiser
algorithm.

```dttk.py``` - Data Transfer ToolKit - a reusable set of classes and algorithms
used to build various different configurations of data transfer systems.

```test_dttk.py``` - host-Python unittest harness for dttk.py.

```perf.py``` - performance monitoring toolkit, used to shine a torchlight on
functions and features that are causing bottleknecks.

```dtcli.py``` - a host-Python only set of command line interface wrappers.
Used by the makefile to run host based testing.

```tasking.py``` - a very tiny cooperative scheduling system, used for tests
that run multiple transfer agents on the same CPU.

```load_pico``` - a script using the 'rshell' utility (```pip3 install rshell```)
to bulk-load any number of connected Raspberry Pi Pico's with the same
codebase.

```makefile``` - a host-only makefile used to automate testing of the system.


## Limitations

* Don't expect this to work on a BBC micro:bit (yet!).

* The receiver path is going through a refactoring, currently it only supports
a single active FileReceiver; this situation will improve when the polled
receive architecture is moved to an inverted callback-based receive 
architecture.

* The main reason for the current receiver-path refactoring, is that the channel 
multiplexing inside LinkReceiver might receive data for a different client; if 
this happens, either a packet must be queued up for the next receive poll for 
that client, or the packet has to be delivered via a callback. Not all demo 
clients use callbacks for data transfer at present.

* The Pico in-built file system, when it writes, can run for up to 32ms
with interrupts disabled while it writes to the flash. Running the UART mode
at 115200bps on the Pico with interrupts disabled, will fill the on-chip
rx FIFO (32 slots) in 2.7ms - so data will be lost when writing to the flash
file system.  The FileWriter components are configured to cache received
data in RAM, and only commit it to the file at the end of the data transfer
when the whole contents are verified. On the host implementation, an alternative
FileWriter is used that writes each block directly to the file. Note that if
using an sdcard driver on the Raspberry Pi Pico, you can safely use the
ImmediateFileWriter, as interrupts are not disabled by the Pico runtime for
a long time, and file corruption doesn't occur.

* We haven't verified the code yet on Adafruit CircuitPython. It is likely to
work, but there are some differences in APIs in CircuitPython, such as where
the UART is imported from, that might make the demos fail to run at present.

## Future Work

* A lot of work is currently going on with optimisation. You can read our
ongoing story about that [here](performance.md)

* We might move over to uasyncio, once the comparative performance between
the tasking.py cooperative scheduling and uascync has been characterised.

* Data-transfer examples for telemetry will be added (e.g. sensor data)

* Further work will be done to significantly improve the transfer performance,
e.g. further improvements to the Buffer object and data slicing operations, and
on the Pico, an assembly language based CRC16 algorithm.

* A demo with the RFM69 radio will be built, that broadcasts data in the
433MHz ISM band and receives files and telemetry on 1 or more ground stations.

* A demo with the RFM95 radio will be built, that broadcasts data on a slow
schedule as a sort of background file transfer service over a LoRa and LoRaWAN
configuration.

* Further work on bringing in SDCard support for storing files, and storing
partial files with their receive bitmaps, to allow recovery from power failure.


David Whale

@whaleygeek

8th Feb 2023
