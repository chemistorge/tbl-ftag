# Running the demos on Host-Python

## loopback test

```bash
$ python3
```

```python
import ftag
ftag.help()
ftag.loopback()
```

## pipeline test between two processes (stdout/stdin)

```bash
$ ./dtcli.py --send test35k.jpg | ./dtcli.py --receive received.jpg
```
