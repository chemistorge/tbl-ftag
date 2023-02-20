# Running the demos on pico-MicroPython

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

NOTE: start the receiver, before you start the sender!

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
