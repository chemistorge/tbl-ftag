# SDTOOL - SD Card experimeter tool

This is a simple tool that allows you to read and write SDCards at the raw
block level. You can also access various setup info from the card, and walk
through partitions to get at the data blocks. 

It is designed to run unmodified on the Raspberry Pi Pico using the default
MicroPython build for the Pico. It could be adapted for use on other platforms
quite easily.

To use it, you need the following two files flashed onto your Raspberry Pi Pico:

```
sdcard.py
sdtool.py
```

## Wiring up your SDCard

Tests were performed using the 
[Adafruit Micro SD SPI or SDIO 3V Breakout Board](https://www.adafruit.com/product/4682)

In the default setup we use this pinning, but you can change the constants
at the top of ```sdcard.py``` if you need a different setup. The CD
(card detect) is not used in this tester.

```python
SPI_N    = 1
GP_SCK   = 10  # output
GP_MOSI  = 11  # output
GP_MISO  = 12  # input
GP_CS    = 13  # output
```

## Running SDTOOL

Just import the module and it runs the tester.

```python
import sdtool
```

A small menu is provided:

```
sdtool - SD card experimenter tool
c:connect i:info m:dumpmbr p:dumppart b:dumpblk W:writetst E:eject? 
```

First connect to the card with the 'c' command. If no card is fitted or
if there is a wiring error, this won't work (and no other commands will work).

Once connected, use the other commands as follows:

## i - Info command

Shows the CID and CSD records from the card.
```
CID: 1B 53 4D 30 30 30 30 30 10 40 87 5E 53 00 DB 5D .SM00000.@.^S..]
CSD: 40 0E 00 32 5B 59 00 00 3A CD 7F 80 0A 40 00 97
```

The [SD-card Physical layer specification (simplified)](https://www.sdcard.org/downloads/pls/) 
from sdcard.org details the format of these two records

## m - Dump Master Boot Record

The master boot record (MBR) holds the primary partition table.
It ends in 55AA if the record is valid. Each primary partition record is
16 bytes in length.

```
000: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
010: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
020: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
030: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
040: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
050: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
060: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
070: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
080: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
090: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
0A0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
0B0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
0C0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
0D0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
0E0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
0F0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
more?
100: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
110: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
120: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
130: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
140: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
150: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
160: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
170: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
180: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
190: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
1A0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
1B0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 FE ................
1C0: FF FF 0B FE FF FF 02 00 00 00 FE 37 EB 00 00 00 ...........7....
1D0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
1E0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
1F0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 55 AA ..............U.
```

## p - Dump the partition table from the MBR

There are 4 records in the MBR partition table. Decode details can be found on the 
[Master Boot Record Wikipedia page](https://en.wikipedia.org/wiki/Master_boot_record)

Type fields are enumerated
[here](https://www.win.tue.nl/~aeb/partitions/partition_types-1.html)

```
p0: 00 FE FF FF 0B FE FF FF 02 00 00 00 FE 37 EB 00
p1: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
p2: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
p3: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00

f:00 first:FFFFFE ty:0B last:FFFFFE LBA:00000002 ns:00EB37FE

0: Region(r_start=2, r_size=15415294) (7892630528 bytes)
1: unused
2: unused
3: unused
```

## b - dump a block in a partition

The first parameter is the MBR partition index [0..4] next parameter is block_no
within that partition. Note, in a FAT partition, block 0 of the partition
has all the useful information in it (and ends in 55AA if it is valid)

```
c:connect i:info m:dumpmbr p:dumppart b:dumpblk W:writetst E:eject? b 0 0
000: EB 58 90 42 53 44 20 20 34 2E 34 00 02 08 20 00 .X.BSD  4.4... .
010: 02 00 00 00 00 F8 00 00 20 00 FF 00 02 00 00 00 ........ .......
020: FE 37 EB 00 B1 3A 00 00 00 00 00 00 02 00 00 00 .7...:..........
030: 01 00 06 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
040: 80 00 29 E8 13 AA FD 57 48 41 4C 45 59 5F 53 44 ..)....WHALEY_SD
050: 20 20 46 41 54 33 32 20 20 20 FA 31 C0 8E D0 BC   FAT32   .1....
060: 00 7C FB 8E D8 E8 00 00 5E 83 C6 19 BB 07 00 FC .|......^.......
070: AC 84 C0 74 06 B4 0E CD 10 EB F5 30 E4 CD 16 CD ...t.......0....
080: 19 0D 0A 4E 6F 6E 2D 73 79 73 74 65 6D 20 64 69 ...Non-system di
090: 73 6B 0D 0A 50 72 65 73 73 20 61 6E 79 20 6B 65 sk..Press any ke
0A0: 79 20 74 6F 20 72 65 62 6F 6F 74 0D 0A 00 00 00 y to reboot.....
0B0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
0C0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
0D0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
0E0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
0F0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
more?
100: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
110: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
120: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
130: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
140: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
150: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
160: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
170: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
180: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
190: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
1A0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
1B0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
1C0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
1D0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
1E0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ................
1F0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 55 AA ..............U.
```

## W - perform a repeated write test (for write speed testing)

This test writes to physical block 4, 16 times, with random data.
It restores the block to its previous values when the test completes.

This is intended to be used to get a measure on how long it takes a card
to commit data to the flash. 

Note that you will get a range of results from your card. On my card,
the first write sometimes takes up to 100ms to complete, but then the next
few hundred writes take about 8ms. SDCards internally do wear levelling,
so it is possible that this discrepancy in write times is the wear levelling
algorithm deciding whether to map the data to a new block (fast) or erase
and use an existing block (much slower).

Also, different speed-class cards will perform differently.

If you decode the CSD record returned from the info command, you can often
identify the advertised response and write times of a particular card.

```
write-test with physical block_no:4
count: 16 avg: 10,829 us
min time: 7,549 us
max time: 35,926 us
```

## E - eject card 

This just invalidates any state that the sdtool has cached about a card.
Use the 'c' command again to connect to a card.

