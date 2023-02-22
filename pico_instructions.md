# Running the demos on pico-MicroPython

For these tests, you might have multiple links configured. If this is the case,
when you import the ftag module, you might get this message, in which case,
choose the U option for the UART link (as radio.py isn't released yet).

```python
>>> import ftag
OPTION=1
[U]ART or [R]adio [UR]? U
>>> 
```

## loading code to both Picos

Install the rshell utility

```bash
pip3 install rshell
```

Connect both Picos via USB to your computer, then use the provided script to
copy all the right files onto (all) connected Pico devices.

```bash
./load_pico
```

## loopback test

Short pins 1 and 2 on Pico (UART0_TX -> UART0_RX)

```bash
# use Thonny, or putty, or on mac/linux, use screen command e.g.
$ screen /dev/tty.usbmodem14211
```

```python
import ftag
ftag.help()
ftag.loopback()
```

## UART based test between two Pico

Connect PicoA(sender) Pin1 to PicoB(receiver) Pin2
Connect PicoA(sender) GND-Pin38 to PicoB(receiver) GND-Pin38

NOTE: best to start the receiver, before you start the sender.
However, the protocol is resilient, and if you get to the END record
before all blocks are received, the receiver will prompt you to re-run
send() to get the remaining blocks.

```python
# use Thonny, or putty, or on mac/linux, use screen command
# on Pico B (receiver)
import ftag
ftag.receive()
```

```python
# use Thonny, or putty, or on mac/linux, use screen command
# on Pico A (sender)
import ftag
ftag.send()
```

## Load the transferred image onto your host PC (using rshell)

```bash
rshell
cp /pyboard/received.jpg .
exit

open received.jpg  # should open and display the image on host PC
```
