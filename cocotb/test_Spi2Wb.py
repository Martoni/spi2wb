import os
import cocotb
import logging
import random

from itertools import repeat

from cocotb.triggers import Timer
from cocotb.result import raise_error
from cocotb.result import TestError, TestFailure
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotb.triggers import RisingEdge
from cocotb.triggers import FallingEdge
from cocotb.triggers import ClockCycles

from cocotbext.spi import *

from cocotbext.wishbone.monitor import WishboneSlave

class TestSpi2Wb(object):

    def __init__(self, dut, datasize, addr_ext, burst,
                 cpol=0, cpha=1, wbdatgen=repeat(int(0))):
        self._dut = dut
        self.log = dut._log
        self._cpol = cpol
        self._cpha = cpha
        self.addr_ext = addr_ext
        self.burst = burst

        self.datasize = datasize

        if cpol == 1:
            raise NotImplementedError("cpol = 1 not implemented yet")
        if cpha == 0:
            raise NotImplementedError("cpha = 0 not implemented yet")

        self._clock = Clock(dut.clock, 50, "ns")
        self._clock_thread = cocotb.start_soon(self._clock.start())

        spi_bus = SpiBus.from_prefix(dut, "io_spi", cs_name='csn')

        self.spi_config = SpiConfig(word_width = 8,
                                    sclk_freq = 1e6,
                                    cpol = False,
                                    cpha = True,
                                    msb_first = True,
                                    data_output_idle = 1,
                                    frame_spacing_ns = 100,
                                    ignore_rx_value = None,
                                    cs_active_low = True)

        self.spimod = SpiMaster(spi_bus, self.spi_config)

        self.wbm = WishboneSlave(dut, "io_wbm", dut.clock,
                                  width=self.datasize,
                                  signals_dict={"cyc": "cyc_o",
                                                "stb": "stb_o",
                                                "we": "we_o",
                                                "adr": "adr_o",
                                                "datwr": "dat_o",
                                                "datrd": "dat_i",
                                                "ack": "ack_i" },
                                  datgen=wbdatgen)

    async def reset(self):
        self._dut.reset.value = 1
        short_per = Timer(100, units="ns")
        await short_per
        self._dut.reset.value = 0
        await short_per

    async def _transfer(self, addr, values=[], write=False):

        b = []

        if self.addr_ext:
            write_bit = 0x8000
            burst_bit = 0x4000
            addr = addr & 0xffff
        else:
            write_bit = 0x80
            burst_bit = 0x40
            addr = addr & 0xff

        if write:
            addr = addr | write_bit

        if self.burst and len(values) > 1:
            addr = addr | burst_bit

        if self.addr_ext:
            b.append((addr >> 8) & 0xff)
            b.append(addr & 0xff)
        else:
            b.append(addr)

        for v in values:
            if self.datasize == 16:
                b.append((v >> 8) & 0xff)
                b.append(v & 0xff)
            else:
                b.append(v & 0xff)

        await self.spimod.write(b, burst = True)
        ret = await self.spimod.read()

        # Remove addr from return values
        if self.addr_ext:
            ret = ret[2:]
        else:
            ret = ret[1:]

        if self.datasize == 16:
            if (len(ret) % 2) != 0:
                raise RuntimeError("Invalid return value")
            else:
                ret16 = []
                for i in range(0, len(ret), 2):
                    ret16.append((ret[i] << 8) | ret[i+1])
                return ret16
        else:
            return ret

    async def write(self, addr, values=[]):
        if (not self.burst) and (len(values) != 1):
            raise NotImplementedError("BURST synthesis option not set")

        await self._transfer(addr, values, write=True)

    async def read(self, addr, nbbyte=1):
        if (not self.burst) and (nbbyte != 1):
            raise NotImplementedError("BURST synthesis option not set")

        b = []
        for _ in range(nbbyte):
            b.append(0x0)

        return await self._transfer(addr, b, write=False)

async def test_write(dut, frames, datasize, extaddr, burst):
    tspi2wb = TestSpi2Wb(dut, datasize, extaddr, burst)
    await tspi2wb.reset()

    for f in frames:
        await tspi2wb.write(f[0], f[1])

    await Timer(10, units="us")

    transaction_count = len(tspi2wb.wbm._recvQ)
    transaction_count_exp = len(frames)
    assert transaction_count == transaction_count_exp, "Incorrect number of transaction received"

    for transaction, f in zip(tspi2wb.wbm._recvQ, frames):
        transaction_len = len(transaction)
        transaction_len_exp = len(f[1])
        assert transaction_len == transaction_len_exp, "Transaction length does not match with frame length"
        addr = f[0]
        for t, wexp in zip(transaction, f[1]):
            assert int(t.adr) == addr, "Bad address @0x{:02X}, expected @0x{:02X}".format(int(t.adr), addr)
            assert int(t.datwr) == wexp, "Value read 0x{:x} @0x{:02X} should be 0x{:02X}".format(int(t.datwr), addr, wexp)
            addr = addr + 1

async def test_read(dut, frames, datasize, extaddr, burst):
    writevalues = []
    for f in frames:
        writevalues = writevalues + f[1]
        if burst:
            writevalues = writevalues + [0x0] # Add extra word to mock cocotbext-wishbone

    tspi2wb = TestSpi2Wb(dut, datasize, extaddr, burst, wbdatgen=iter(writevalues))
    await tspi2wb.reset()

    readframes = []
    for f in frames:
        readframes.append(await tspi2wb.read(f[0], nbbyte=len(f[1])))

    await Timer(10, units="us")

    transaction_count = len(tspi2wb.wbm._recvQ)
    assert transaction_count == len(frames), "Incorrect transaction count received"

    for transaction, f in zip(tspi2wb.wbm._recvQ, frames):
        exp_transaction_len = len(f[1])
        if burst:
            exp_transaction_len = exp_transaction_len + 1 # Add the extra transaction
        assert len(transaction) == exp_transaction_len, "Transaction too short"
        addr = f[0]
        for t, expval in zip(transaction, f[1]):
            assert int(t.adr) == addr, "Bad address @0x{:02X}, expected @0x{:02X}".format(int(t.adr), addr)
            assert int(t.datrd) == expval, "Value read 0x{:x} @0x{:02X} should be 0x{:02X}".format(t.datrd, f[0], expval)
            addr = addr + 1

# Get environment variables
datasize = int(os.environ['DATASIZE'])

if not datasize in [8, 16]:
    raise NotImplementedError("Size {} not supported".format(datasize))

extaddr = False
try:
    if os.environ['EXTADDR'] == "1":
        extaddr = True
except KeyError:
    pass

burst = False
try:
    if os.environ['BURST'] == "1":
        burst = True
except KeyError:
    pass

random.seed(1712317)

#Test parameters
max_num_frames = 10
num_test_set = 4
max_burst_frame_len = 10

switch_max_addr = {
    #extaddr, burst
    (False, False): 0x7f,
    (False, True): 0x3f,
    (True, False): 0x7fff,
    (True, True): 0x3fff
    }

max_addr = switch_max_addr.get((extaddr, burst))
max_val = 0xff if datasize == 8 else 0xffff
max_len = 1 if not burst else max_burst_frame_len

def generate_test_sets():
    test_sets = []
    for _ in range(num_test_set):
        num_frames = random.randint(1, max_num_frames)
        frames = []
        for _ in range(num_frames):
            length = random.randint(1, max_len)
            addr = random.randint(0, max_addr)
            values = [random.randint(0, max_val) for _ in range(length)]
            f = (addr, values)
            frames.append(f)

        test_sets.append(frames)

    return test_sets

write_test_sets = generate_test_sets()
read_test_sets = generate_test_sets()

tf_test_write = cocotb.regression.TestFactory(test_function=test_write, datasize=datasize, extaddr=extaddr, burst=burst)
tf_test_write.add_option(name='frames', optionlist=write_test_sets)
tf_test_write.generate_tests()

tf_test_read = cocotb.regression.TestFactory(test_function=test_read, datasize=datasize, extaddr=extaddr, burst=burst)
tf_test_read.add_option(name='frames', optionlist=read_test_sets)
tf_test_read.generate_tests()
