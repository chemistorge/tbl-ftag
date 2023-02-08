# Running the demos on Host-Python

## Auto tests - using the makefile

```bash
make clean tests
```

## loopback test - using the makefile

```bash
make clean test_loopback
```

## loopback test - using Python

```bash
$ python3
```

```python
import ftag
ftag.help()
ftag.loopback()
```

## pipeline test - using the makefile

```bash
make clean test_pipeline
```

## pipeline test between two processes (stdout/stdin)

```bash
$ ./dtcli.py --send test35k.jpg | ./dtcli.py --receive received.jpg
```

## pipeline test via a file

```bash
#sender
    ./dtcli.py --send test35k.jpg | ./dtcli.py --bin2hex > ENCODED

#receiver
    cat ENCODED | ./dtcli.py --hex2bin | ./dtcli.py --receive received.jpg
```

## pipeline test via a network socket

```bash
#listener:
    nc -l 9999 | ./dtcli.py --receive received.jpg

sender:
    ./dtcli.py --send test35k.jpg | nc localhost 9999
```

NOTE: ```nc``` is the macosx name for the ```netcat``` tool - use ```netcat``` 
on linux systems.

