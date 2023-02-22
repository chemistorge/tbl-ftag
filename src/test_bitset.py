# test_bitset.py  21/02/2023  D.J.Whale

import random
from dttk import BitSet

def test_random():
    SIZE = round(35000/50)
    ##SIZE = 1000
    b = BitSet(SIZE)

    while not b.is_complete():
        i = random.randint(0,SIZE-1)
        b[i] = 1
        print(str(b))
    print(repr(b))

def test_deterministic():
    SIZE = round(35000/50)
    b = BitSet(SIZE)

    print("-", str(b))
    for i in range(SIZE):  # set the first 11 bits
        b[i] = 1
        print(i, str(b))

if __name__ == "__main__":
    test_random()
    test_deterministic()