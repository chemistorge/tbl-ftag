#! /usr/bin/env python3
# test_all.py  10/01/2023  D.J.Whale
#NOTE: works on HOST python only

import unittest

import ftag  # does an auto-dependency check for host
import dttk


#----- BYTESTREAM GENERATOR ----------------------------------------------------
class ByteStreamGenerator(dttk.Link):
    """Each call gives the next byte, EOF marked with None"""
    # provides a way to generate simulated received data
    def __init__(self, data:bytes):
        dttk.Link.__init__(self)
        self._data = data
        self._idx = 0

    def recvinto(self, buf:dttk.Buffer, info:dict or None=None, wait:bool=False) -> int or None:
        """Copy as much data in as we have and buf will accept"""
        _ = info  # argused
        remaining = len(self._data) - self._idx
        if remaining == 0: return None  #EOF

        space     = buf.get_max() - len(buf)  #buf.get_space()?
        use       = min(remaining, space)

        wanted_data = self._data[self._idx:self._idx+use]
        buf.extend(wanted_data)
        self._idx += use
        ##print("Byte stream generator used %d bytes (%s)" % (use, str(wanted_data)))
        return use

class TestGenerator(unittest.TestCase):
    def test_generator(self):
        gen = ByteStreamGenerator(b'hello')
        b = dttk.Buffer()

        # first poll gets data
        nb = gen.recvinto(b)
        self.assertEqual(5, nb)
        self.assertEqual(b'hello', b.get_slice(0, len(b)))

        # poll again and get NODATA (or None for EOF)
        b.reset()
        nb = gen.recvinto(b)
        self.assertEqual(None, nb)

#----- TEST BUFFER -------------------------------------------------------------
#NOTE: test get_max()
#NOTE: test is_full()

class TestBuffer(unittest.TestCase):
    def expect_exception(self):
        self.fail("did not get expected exception")

    #----- INITIAL HAPPY CASE TESTS
    def test_create(self):
        """create default buffer"""
        buf = dttk.Buffer()
        EXPECTED = "Buffer(sz:128, start:10, end:10)"
        actual = str(buf)
        self.assertEqual(EXPECTED, actual)

    def test_extend(self):
        """append some items and get them back"""
        buf = dttk.Buffer()
        # int
        buf.append(1)
        buf.append(2)
        # bytes
        buf.extend(b'ABC')
        # bytearray
        buf.extend(bytearray([3,4,5]))

        EXPECTED = b'\x01\x02ABC\x03\x04\x05'
        actual = buf.get_slice(0, len(buf))
        self.assertEqual(EXPECTED, actual)

    def test_prepend(self):
        """prepend some items and get them back"""
        buf = dttk.Buffer()
        # int
        buf.prepend1(1)
        # bytes
        buf.prepend(b'\x02\x03\x04')
        # bytearray
        buf.prepend(bytearray(b'ABC'))
        EXPECTED = b'ABC\x02\x03\x04\x01'
        actual = buf.get_slice(0, len(buf))
        self.assertEqual(EXPECTED, actual)

    def test_len(self):
        """get the length of a soft growing buffer"""
        buf = dttk.Buffer()
        actual = []
        actual.append(len(buf))
        buf.append(1)
        actual.append(len(buf))
        buf.prepend1(2)
        actual.append(len(buf))
        EXPECTED = [0, 1, 2]
        self.assertEqual(EXPECTED, actual)

    def test_ltrunc(self):
        """ltrunc to remove headers, check length changes"""
        buf = dttk.Buffer()
        buf.extend(b'ABCD1234')
        buf.ltrunc(4)
        EXPECTED = b'1234'
        actual = buf.get_slice(0, len(buf))
        self.assertEqual(EXPECTED, actual)
        self.assertEqual(4, len(buf))

    def test_rtrunc(self):
        """rtrunc to remove footers, check length changes"""
        buf = dttk.Buffer()
        buf.extend(b'ABCD1234')
        buf.rtrunc(4)
        EXPECTED = b'ABCD'
        actual = buf.get_slice(0, len(buf))
        self.assertEqual(EXPECTED, actual)
        self.assertEqual(4, len(buf))

    def test_iter(self):
        """iterate items in buffer"""
        buf = dttk.Buffer()
        buf.extend(b'12345678')
        res = []
        for b in buf:
            res.append(chr(b))
        EXPECTED = ['1', '2', '3', '4', '5', '6', '7', '8']
        self.assertEqual(EXPECTED, res)

    #DEPRECATED: lock() unlock()
    # def test_lock_unlock(self):
    #     """lock and unlock"""
    #     actual = []
    #     buf = dttk.Buffer()
    #     buf.lock()
    #     buf.lock()
    #     actual.append(str(buf))
    #
    #     buf.unlock()
    #     buf.unlock()
    #     actual.append(str(buf))
    #
    #     buf.lock("secret")
    #     buf.lock("secret")
    #     actual.append(str(buf))
    #
    #     buf.unlock("secret")
    #     buf.unlock("secret")
    #     actual.append(str(buf))
    #     # expect no exceptions
    #
    #     EXPECTED = [
    #         'Buffer(sz:128, start:10, end:10, locked:True, pw:None)',
    #         'Buffer(sz:128, start:10, end:10, locked:False, pw:None)',
    #         'Buffer(sz:128, start:10, end:10, locked:True, pw:secret)',
    #         'Buffer(sz:128, start:10, end:10, locked:False, pw:None)'
    #     ]
    #     self.assertEqual(EXPECTED, actual)

    def test_reset(self):
        """reset and check len"""
        actual = []
        buf = dttk.Buffer()
        buf.extend(b'12345678')
        actual.append(str(buf))
        buf.reset()
        actual.append(str(buf))

        EXPECTED = [
            'Buffer(sz:128, start:10, end:18)',
            'Buffer(sz:128, start:10, end:10)'
        ]
        self.assertEqual(EXPECTED, actual)

    #----- MORE CHALLENGING HAPPY CASE TESTS
    def test_create_from(self):
        """create from existing"""
        # bytes
        EXPECTED = b'ABCD'
        buf = dttk.Buffer(b'ABCD')
        actual = buf.get_slice(0, len(buf))
        self.assertEqual(EXPECTED, actual)

        # bytearray
        EXPECTED = b'1234'
        buf = dttk.Buffer(bytearray(b'1234'))
        actual = buf.get_slice(0, len(buf))
        self.assertEqual(EXPECTED, actual)

    #DEPRECATED: rgrow()
    # def test_prepend_rshift(self):
    #     """prepend and exceed the initial start, forces an rshift"""
    #     buf = dttk.Buffer(b'ABCD')
    #     prefix = bytes('1234' + ('*' * dttk.Buffer.DEFAULT_START), encoding='UTF-8')
    #     buf.prepend(prefix)
    #     EXPECTED = b'1234**********ABCD'
    #     actual = buf.get_slice(0, len(buf))
    #     self.assertEqual(EXPECTED, actual)

    #DEPRECATED rgrow()
    # def test_append_rgrow(self):
    #     """append and exceed the buffer size to forces an rgrow"""
    #     buf = dttk.Buffer(initial_size=4)
    #     res = []
    #     res.append(str(buf))
    #
    #     buf.extend(b'1234') # now full
    #     res.append(str(buf))
    #
    #     buf.extend(b'ABCD')
    #     res.append(str(buf))
    #     res.append(str(buf.get_slice(0, len(buf))()))
    #
    #     EXPECTED = [
    #         'Buffer(sz:4, start:0, end:0, locked:False, pw:None)',
    #         'Buffer(sz:4, start:0, end:4, locked:False, pw:None)',
    #         'Buffer(sz:8, start:0, end:8, locked:False, pw:None)',
    #         "b'1234ABCD'"
    #     ]
    #     self.assertEqual(EXPECTED, res)

    #DEPRECATED lock()
    # def test_double_lock(self):
    #     """double lock ok as long as no/same password"""
    #     res = []
    #     buf = dttk.Buffer()
    #     buf.lock()
    #     buf.lock()
    #     res.append(str(buf))
    #
    #     buf = dttk.Buffer()
    #     buf.lock("fred")
    #     buf.lock("fred")
    #     res.append(str(buf))
    #
    #     EXPECTED = [
    #         'Buffer(sz:128, start:10, end:10, locked:True, pw:None)',
    #         'Buffer(sz:128, start:10, end:10, locked:True, pw:fred)'
    #     ]
    #     self.assertEqual(EXPECTED, res)

    #DEPRECATED: unlock()
    # def test_double_unlock(self):
    #     """double unlock ok as long as password matches on first unlock"""
    #     res = []
    #     buf = dttk.Buffer()
    #     buf.lock()
    #     res.append(str(buf))
    #     buf.unlock()
    #     buf.unlock()
    #     res.append(str(buf))
    #
    #     buf = dttk.Buffer()
    #     buf.lock("fred")
    #     res.append(str(buf))
    #     buf.unlock("fred")
    #     buf.unlock("fred")
    #     res.append(str(buf))
    #
    #     EXPECTED = [
    #         'Buffer(sz:128, start:10, end:10, locked:True, pw:None)',
    #         'Buffer(sz:128, start:10, end:10, locked:False, pw:None)',
    #         'Buffer(sz:128, start:10, end:10, locked:True, pw:fred)',
    #         'Buffer(sz:128, start:10, end:10, locked:False, pw:None)'
    #     ]
    #     self.assertEqual(EXPECTED, res)


    #----- ERROR CASE TESTS
    def test_non_int_index_ERR(self):
        """non integer index"""
        buf = dttk.Buffer()
        # getitem
        try:
            i = buf["a"]
            self.expect_exception()
        except TypeError: pass

        #DEPRECATED: setitem()
        # # setitem
        # try:
        #     buf["a"] = 1
        #     self.expect_exception()
        # except ValueError: pass

    def test_index_range_ERR(self):
        """out of range index"""
        buf = dttk.Buffer(b'1234')
        # getitem
        try:
            i = buf[200]
            self.expect_exception()
        except IndexError: pass

        #DEPRECATED: setitem()
        # # setitem
        # try:
        #     buf[4] = 1
        #     self.expect_exception()
        # except IndexError: pass

    #DEPRECATED: lock()
    # def test_lock_locked_wrong_password_ERR(self):
    #     """lock an already locked buffer with diff password"""
    #     buf = dttk.Buffer()
    #     buf.lock("fred")
    #     try:
    #         buf.lock("bert")
    #         self.expect_exception()
    #     except dttk.Buffer.LockedError: pass

    #DEPRECATED: unlock()
    # def test_unlock_wrong_password_ERR(self):
    #     """unlock with wrong password"""
    #     buf = dttk.Buffer()
    #     buf.lock("fred")
    #
    #     try:
    #         buf.unlock("bert")
    #         self.expect_exception()
    #     except dttk.Buffer.LockedError:pass

    #DEPRECATED: lock()
    # def test_mutate_locked_ERR(self):
    #     """mutate a locked buffer"""
    #     buf = dttk.Buffer(b'ABCD')
    #     buf.lock()
    #
    #     # setitem
    #     try:
    #         buf[0] = 1
    #         self.expect_exception()
    #     except dttk.Buffer.ImmutableModifyError: pass
    #
    #     # create_from
    #     try:
    #         buf.create_from(b'1234')
    #         self.expect_exception()
    #     except dttk.Buffer.ImmutableModifyError: pass
    #
    #     # prepend
    #     try:
    #         buf.prepend(b'1234')
    #         self.expect_exception()
    #     except dttk.Buffer.ImmutableModifyError: pass
    #
    #     # extend
    #     try:
    #         buf.extend(b'1234')
    #         self.expect_exception()
    #     except dttk.Buffer.ImmutableModifyError: pass
    #
    #     # ltrunc
    #     try:
    #         buf.ltrunc(1)
    #         self.expect_exception()
    #     except dttk.Buffer.ImmutableModifyError: pass
    #
    #     # rtrunc
    #     try:
    #         buf.rtrunc(1)
    #         self.expect_exception()
    #     except dttk.Buffer.ImmutableModifyError: pass
    #
    #     # reset
    #     try:
    #         buf.reset()
    #         self.expect_exception()
    #     except dttk.Buffer.ImmutableModifyError: pass


#----- TEST RADIO --------------------------------------------------------------
class TestRadio(unittest.TestCase):
    def test_stdstream_radio(self):
        #NOTE, will get this data on stdout
        ssr = dttk.StdStreamRadio()
        send = ssr.send

        buf = dttk.Buffer(b'hello world')
        send(buf)

        buf = dttk.Buffer(b'\x01\x02\x03\x04')
        send(buf)

    def test_mock_radio(self):
        EXPECTED = b'hello world'
        r = dttk.InMemoryRadio()
        buf = dttk.Buffer(b'hello world')
        r.send(buf)

        buf = dttk.Buffer()
        r.recvinto(buf)
        data = buf.get_slice(0, len(buf))
        self.assertEqual(EXPECTED, data)

#----- TEST PACKETISER SEND ----------------------------------------------------
class TestPacketiserSend(unittest.TestCase):
    """Test the sender encoder"""
    def setUp(self):
        class Sender(dttk.Link):
            def __init__(self):
                dttk.Link.__init__(self)
                self._capture = bytearray()

            def send(self, data, info=None) -> None:
                _ = info  # argused
                for i in data:
                    self._capture.append(i)

            def get_sent(self):
                return self._capture

        self._sender = Sender()
        self._p = dttk.Packetiser(self._sender)

    def do_send(self, data:str or bytes) -> bytes:
        self._p.send(data)
        return bytes(self._sender.get_sent())

    def test_tx_data(self):
        EXPECTED = b'\xFFhello\xFF'
        actual = self.do_send(b'hello')
        self.assertEqual(EXPECTED, actual)

    def test_tx_sync_in_data(self):
        EXPECTED = b'\xff**\xfe\xfd**\xff'
        actual = self.do_send(b'**\xFF**')
        self.assertEqual(EXPECTED, actual)

    def test_tx_esc_in_data(self):
        EXPECTED = b'\xff**\xfe\xfe**\xff'
        actual = self.do_send(b'**\xFE**')
        self.assertEqual(EXPECTED, actual)

# ----- TEST PACKETISER RECEIVE -------------------------------------------------
class TestPacketiserReceive(unittest.TestCase):

    def test_rx_junk(self):
        """Junk with no sync is just junk and dropped"""
        EXPECTED = None  # reads no data, then gets EOF
        gen = ByteStreamGenerator(b"hello")
        p = dttk.Packetiser(gen)
        b = dttk.Buffer()

        nb = p.recvinto(b)

        self.assertEqual(EXPECTED, nb)

    def test_rx_packet(self):
        """A valid sync wrapped packet is returned"""
        EXPECTED = b'hello'
        gen = ByteStreamGenerator(b'\xFFhello\xFF')
        b = dttk.Buffer()
        p = dttk.Packetiser(gen)

        nb = p.recvinto(b)

        self.assertEqual(5, nb)
        actual = b.get_slice(0, len(b))
        self.assertEqual(EXPECTED, actual)

    def test_rx_junk_sync(self):
        """Junk followed by sync followed by data, returns just data"""
        EXPECTED = b'hello'
        gen = ByteStreamGenerator(b'1234\xFFhello\xFF')
        b = dttk.Buffer()
        p = dttk.Packetiser(gen)

        nb = p.recvinto(b)
        actual = b.get_slice(0, len(b))

        self.assertEqual(5, nb)
        self.assertEqual(EXPECTED, actual)

    def test_rx_FF_in_data(self):
        """An escaped FF is correctly decoded"""
        EXPECTED = b'**\xff**'
        gen = ByteStreamGenerator(b'\xFF**\xFE\xFD**\xFF')
        b = dttk.Buffer()
        p = dttk.Packetiser(gen)

        p.recvinto(b)
        actual = b.get_slice(0, len(b))

        self.assertEqual(EXPECTED, actual)

    def test_rx_esc_in_data(self):
        """an escaped escape is correctly decoded"""
        EXPECTED = b'**\xfe**'
        gen = ByteStreamGenerator(b'\xFF**\xFE\xFE**\xFF')
        p = dttk.Packetiser(gen)
        b = dttk.Buffer()

        p.recvinto(b)

        actual = b.get_slice(0, len(b))
        self.assertEqual(EXPECTED, actual)

    def test_rx_bad_esc(self):
        """A FE(non FC,FC) character should be handled consistently"""
        gen = ByteStreamGenerator(b'\xFFone\xFE\x02rest\xFF\xFFtwo\xFF')
        p = dttk.Packetiser(gen)
        b = dttk.Buffer()

        EXPECTED1 = b'one\x02rest'
        p.recvinto(b)
        actual1 = b.get_slice(0, len(b))
        self.assertEqual(EXPECTED1, actual1)

        EXPECTED2 = b'two'
        b.reset()
        p.recvinto(b)
        actual2 = b.get_slice(0, len(b))
        self.assertEqual(EXPECTED2, actual2)

    #NOTE: the Packetiser might need to handle this itself now
    def FAILtest_rx_truncate_long(self):
        """A long packet is truncated and dropped, resync to next packet"""
        #NOTE, no return on truncated packet, if more to process

        EXPECTED = b'ABCD'

        gen = ByteStreamGenerator(b'\xFF12345678\xFF\xFFABCD\xFF')
        p = dttk.Packetiser(gen)
        b = dttk.Buffer(size=7)

        p.recvinto(b)
        actual = b.get_slice(0, len(b))

        self.assertEqual(EXPECTED, actual)

    def test_rx_single_sync(self):
        """A single sync should still work"""
        gen = ByteStreamGenerator(b'\xFFone\xFFtwo\xFF')
        p = dttk.Packetiser(gen)
        b = dttk.Buffer()

        EXPECTED = b'one'
        p.recvinto(b)
        actual = b.get_slice(0, len(b))
        self.assertEqual(EXPECTED, actual)

        EXPECTED = b'two'
        b.reset()
        p.recvinto(b)
        actual = b.get_slice(0, len(b))
        self.assertEqual(EXPECTED, actual)

        b.reset()
        EXPECTED = b''
        p.recvinto(b)
        actual = b.get_slice(0, len(b))
        self.assertEqual(EXPECTED, actual)

    def test_rx_long_sync_run(self):
        """A long run of syncs should be seen as a sync boundary"""
        gen = ByteStreamGenerator(b'\xFF\xFF\xFF\xFFone\xFF')
        p = dttk.Packetiser(gen)
        b = dttk.Buffer()

        EXPECTED = b'one'
        p.recvinto(b)
        actual = b.get_slice(0, len(b))
        self.assertEqual(EXPECTED, actual)

        EXPECTED = b''
        b.reset()
        p.recvinto(b)
        actual = b.get_slice(0, len(b))
        self.assertEqual(EXPECTED, actual)

    def test_rx_sync_in_esc(self):
        """A sync inside an esc should trash current packet and resync"""
        gen = ByteStreamGenerator(b'\xFFone\xFE\xFFrest\xFF\xFFtwo\xFF')
        p = dttk.Packetiser(gen)
        b = dttk.Buffer()

        EXPECTED = b'rest'
        p.recvinto(b)
        actual = b.get_slice(0, len(b))
        self.assertEqual(EXPECTED, actual)

        EXPECTED = b'two'
        b.reset()
        p.recvinto(b)
        actual = b.get_slice(0, len(b))
        self.assertEqual(EXPECTED, actual)


#----- TEST PACKETISER BOTH ----------------------------------------------------

class DummyRadio:
    """A memory radio that allows us to give a list of receive packet sizes"""
    #this allows us to replicate a specific receiver packet length pattern
    #as a way to exercise a specific receive in a deterministic way
    def __init__(self):
        self._tx_queue = bytearray()
        self._rx_pattern = [56, 59, 59, 59, 59, 59, 59, 59, 59, 59, 59, 59, 32, 59, 32, 59, 32, 59, 32, 59, 32, 59, 32, 59, 32, 59, 32, 59, 32, 59, 32, 59, 32, 59, 32, 59, 32, 59, 32, 59, 32, 59, 59, 59, 59, 59, 59, 59, 59, 15, 11]
        self._rx_idx = 0

    def send(self, data:dttk.Buffer or None) -> bool:
        # just keep pumping bytes into the tx queue
        if data is None:  return False  # could be used to CLOSE_CONNECTION/EOF
        packet = data.get_slice(0, len(data))
        ##print("DummyRadio:send:%d %s" % (len(packet), dttk.hexstr(packet)))

        self._tx_queue.extend(packet)
        ##print("  tx queue now:%d" % len(self._tx_queue))
        return True  # queued for transmit

    def _get_next_nb(self) -> int or None:
        """Get the next numbytes to use from the pattern"""
        if self._rx_idx >= len(self._rx_pattern):
            return None  #EOF
        nb = self._rx_pattern[self._rx_idx]
        self._rx_idx += 1
        return nb

    def recvinto(self, buf:dttk.Buffer, info:dict or None=None, wait:bool=False) -> int or None:
        # blocking receive, assumes we always transmit first to the queue
        nb = self._get_next_nb()
        ##print("recvinto: next nb:%s" % nb)
        if nb is None: nb = len(self._tx_queue)
        actual_nb = min(buf.get_max(), nb)

        # read/remove nb from start of queue
        packet = self._tx_queue[:actual_nb]
        self._tx_queue = self._tx_queue[actual_nb:]

        # put that packet into the user buffer
        buf.reset()
        buf.extend(packet)
        nb = len(packet)
        ##print("DummyRadio:recv %s %s" % (nb, dttk.hexstr(packet)))
        return nb

#IDEA: use a Packetiser factory method to do this class wrapping
#then we can pass DummyRadio(rxlens) to it.
class PacketisedDummyRadio(dttk.Link):
    def __init__(self):
        dttk.Link.__init__(self)
        dr = DummyRadio()
        self._send_packetiser = dttk.Packetiser(dr)  #NOTE: need a way to pass the rxlens
        self._recv_packetiser = dttk.Packetiser(dr)
        # direct dispatch, faster
        self.send = self._send_packetiser.send
        ##self.recvinto = self._packetiser.recvinto

    def recvinto(self, buf:dttk.Buffer, info:dict or None=None, wait:bool=False) -> int or None:
        nb = self._recv_packetiser.recvinto(buf, info, wait=True)
        ##print("Packetiser.recvinto:%s %s" % (nb, dttk.hexstr(buf.get_slice(0, len(buf)))))
        assert nb is not None, "<<recvinto HERE"  #temporary hard stop
        return nb

class TestPacketiserBoth(unittest.TestCase):
    """Test both send and receive together"""
    def tearDown(self):
        dttk.packetiser_stats.reset()

    # def test_sendbytes(self):
    #     """Send a run of bytes via packetiser and get the same back"""
    # rad = dttk.InMemoryRadio()
    # self.sender = dttk.Packetiser(rad)
    # self.receiver = dttk.Packetiser(rad)
    # self.tx_buf = dttk.Buffer()
    # self.rx_buf = dttk.Buffer()
    #     DATA = b'*ABCD*'
    #     raw = bytes([len(DATA)]) + DATA
    #     self.tx_buf.create_from(raw)
    #     self.sender.send(self.tx_buf)
    #
    #     nb = self.receiver.recvinto(self.rx_buf, info={"trace":1})
    #
    #     self.assertEqual(len(raw), nb)
    #     actual = self.rx_buf.get_slice(0, len(self.rx_buf))
    #     self.assertEqual(raw, actual)
    #
    #     print(dttk.packetiser_stats)  #DIAGS

    def test_send_file(self):
        """Send a whole file"""
        TX_FILENAME = "testdata.txt"
        ##TX_FILENAME = "dttk.py"
        ##TX_FILENAME = "stars.txt"
        RX_FILENAME = "received.txt"
        rad = PacketisedDummyRadio()  #NOTE: pass nb receive pattern here
        link_manager = dttk.LinkManager(rad)
        BLOCK_SIZE = 50

        def send_file_task(filename:str) -> None: # or exception
            """Non-blocking sender for a single file (as a task that has a tick())"""
            return dttk.FileSender(filename, link_manager, progress_fn=None, blocksz=BLOCK_SIZE)

        def receive_file_task(filename: str) -> None:  # or exception
            """Non-blocking receiver"""
            return dttk.FileReceiver(link_manager, filename, progress_fn=None)

        # send the whole file via packetiser/link into the tx_queue first
        # as it means the receiver never blocks (NOTE might be a bad idea?)
        send_file_task(TX_FILENAME).run()

        # now receive from the tx queue
        receive_file_task(RX_FILENAME).run()

#----- TEST LINK RECEIVER ------------------------------------------------------
class TestLinkReceiver(unittest.TestCase):
    def test_short_header(self):
        """length byte too small for a valid payload"""
        ##EXPECTED_ERROR  = "packet too short to have a header"
        EXPECTED_RESULT = b''

        gen = ByteStreamGenerator(b'\x02\x01\x00')
        receiver = dttk.LinkReceiver(gen)

        buf = dttk.Buffer()
        receiver.recvinto(buf)
        result = buf.get_slice(0, len(buf))

        ##self.assertEqual(EXPECTED_ERROR, receiver.get_error())
        self.assertEqual(EXPECTED_RESULT, result)

    def test_crc_valid(self):
        """valid CRC returns a payload"""
        ##EXPECTED_ERROR = None
        EXPECTED_RESULT = b''  # it's an empty payload with valid CRC
        gen = ByteStreamGenerator(b'\x04\x00\x00\xCD\xCC')

        receiver = dttk.LinkReceiver(gen)
        buf = dttk.Buffer()
        receiver.recvinto(buf)
        result = buf.get_slice(0, len(buf))
        ##self.assertEqual(EXPECTED_ERROR, receiver.get_error())
        self.assertEqual(EXPECTED_RESULT, result)

    def test_crc_invalid(self):
        """invalid CRC returns no payload"""
        ##EXPECTED_ERROR = "crc failure for:040000CDCD expected:CDCC got:CDCD"
        EXPECTED_RESULT = b''
        gen = ByteStreamGenerator(b'\x04\x00\x00\xCD\xCD')
        receiver = dttk.LinkReceiver(gen)

        buf = dttk.Buffer()
        receiver.recvinto(buf)
        result = buf.get_slice(0, len(buf))

        ##self.assertEqual(EXPECTED_ERROR, receiver.get_error())
        self.assertEqual(EXPECTED_RESULT, result)

    def test_dropped_payload(self):
        """A jump in seqno reports seqno mismatch"""
        ##EXPECTED_ERROR = "seqno mismatch want:00 got:01; resyncing"
        EXPECTED_RESULT = b''
        gen = ByteStreamGenerator(b'\x04\x01\x00\xFE\xFD')
        receiver = dttk.LinkReceiver(gen)

        buf = dttk.Buffer()
        receiver.recvinto(buf)
        result = buf.get_slice(0, len(buf))

        ##self.assertEqual(EXPECTED_ERROR, receiver.get_error())
        self.assertEqual(EXPECTED_RESULT, result)

    def test_single_bit_error(self):
        """a single bit error causes the CRC should fail"""
        ##EXPECTED_ERROR = "crc failure for:0500002B377D expected:275C got:377D"
        EXPECTED_RESULT = b''
        gen = ByteStreamGenerator(b'\x05\x00\x00\x2B\x37\x7D')
        receiver = dttk.LinkReceiver(gen)

        buf = dttk.Buffer()
        nb = receiver.recvinto(buf)
        result = buf.get_slice(0, len(buf))

        ##self.assertEqual(EXPECTED_ERROR, receiver.get_error())
        self.assertEqual(EXPECTED_RESULT, result)

    def test_single_byte_error(self):
        """A single byte error causes the CRC to fail"""
        ##EXPECTED_ERROR = "crc failure for:050000FF377D expected:ACA5 got:377D"
        EXPECTED_RESULT = b''
        gen = ByteStreamGenerator(b'\x05\x00\x00\xFF\x37\x7D')
        receiver = dttk.LinkReceiver(gen)

        buf = dttk.Buffer()
        nb = receiver.recvinto(buf)
        result = buf.get_slice(0, len(buf))

        ##self.assertEqual(EXPECTED_ERROR, receiver.get_error())
        self.assertEqual(EXPECTED_RESULT, result)


#----- INTERACTIVE TESTER ------------------------------------------------------
class InteractiveLink(dttk.Link):
    @staticmethod
    def send(data, info: dict or None = None) -> None:
        _ = info  # argused
        print("data:%s" % str(data))

    @staticmethod
    def recvinto(user_buf:dttk.Buffer, info:dict or None=None) -> int or None:
        assert isinstance(user_buf, dttk.Buffer), "want:Buffer, got:%s" % str(type(user_buf))
        _ = info  # argused
        l = user_buf.get_max()
        try:
            d = input("data(%d)> " % l)
            if d == "": return 0  #NODATA
        except EOFError:
            return None  #EOF

        d = str.encode(d)
        d = bytearray(d)
        d = d.replace(b'*', b'\xFF')
        if len(d) > l: d = d[l]  # max_len
        user_buf.extend(d)
        return l

def test_packetiser():
    """Simple interactive tester"""
    p = dttk.Packetiser(InteractiveLink())
    b = dttk.Buffer()

    while True:
        res = p.recvinto(b)
        if res is None: #EOF
            print("EOF")
            break
        if res == 0: #NODATA
            print("NODATA")
        else:
            print("DATA:%s" % str(b.get_slice(0, len(b))))
            b.reset() # only clear, once it is used

if __name__ == "__main__":
    try:
        unittest.main()
    except KeyboardInterrupt:
        print("\nCTRL-C")
