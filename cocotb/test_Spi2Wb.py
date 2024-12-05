import os
import cocotb
import logging

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

DATASIZE = os.environ['DATASIZE']

try:
    EXTADDR = os.environ['EXTADDR']
except KeyError:
    EXTADDR = "0"

Tone_data_frame = True
Tburst_read = False

try:
    BURST = os.environ['BURST']
    if BURST == "1":
        Tburst_read = True
        Tone_data_frame = False
except KeyError:
    BURST = "0"

class TestSpi2Wb(object):

    def __init__(self, dut, cpol=0, cpha=1,
                 datasize=DATASIZE, addr_ext=EXTADDR,
                 burst=BURST, wbdatgen=repeat(int(0))):
        self._dut = dut
        self.log = dut._log
        self._cpol = cpol
        self._cpha = cpha
        if addr_ext == "1":
            self.log.info("Extended spi address mode")
            self.addr_ext = True
        else:
            self.log.info("Simple spi address mode")
            self.addr_ext = False
        if burst == "1":
            self.log.info("Burst enabled mode")
            self.burst = True
        else:
            self.burst = False

        if not int(datasize) in [8, 16]:
            raise NotImplementedError("Size {} not supported".format(datasize))

        self.datasize = int(datasize)

        switch = {
            #extaddr, burst
            (False, False): 7,
            (False, True): 6,
            (True, False): 15,
            (True, True): 14
            }

        self.addresswidth = switch.get((self.addr_ext, self.burst))

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

@cocotb.test(skip=not Tburst_read)
async def test_burst_write(dut):
    tspi2wb = TestSpi2Wb(dut)
    if tspi2wb.addr_ext:
        dut._log.info("Address is extended to 14bits")
    await tspi2wb.reset()

    addr = 0x10
    testvalues = [(addr, (0xaa<<8 | addr)) for addr in range(addr,addr + 6)]
    writevalues = [value[-1] for value in testvalues]

    # fill memory with burst
    await tspi2wb.write(addr, writevalues)
    await Timer(10, units="us")

    transaction_count = len(tspi2wb.wbm._recvQ)
    assert transaction_count == 1, f"Received {transaction_count}, expected 1"

    for transaction, (addr, expvalue) in zip(tspi2wb.wbm._recvQ, testvalues):
        for t in transaction:
            assert int(t.adr) == addr, "Bad address @0x{:02X}, expected @0x{:02X}".format(int(t.adr), addr)
            assert int(t.datwr) == expvalue, "Value read 0x{:x} @0x{:02X} should be 0x{:02X}".format(int(t.datwr), addr, expvalue)
            expvalue = expvalue + 1
            addr = addr + 1

@cocotb.test(skip=not Tburst_read)
async def test_burst_read(dut):
    addr = 0x10
    testvalues = [(addr, (0xaa<<8 | addr)) for addr in range(addr,addr + 6)]
    writevalues = [value[-1] for value in testvalues]

    tspi2wb = TestSpi2Wb(dut, wbdatgen=iter(writevalues + [0xff]))
    if tspi2wb.addr_ext:
        dut._log.info("Address is extended to 14bits")
    await tspi2wb.reset()

    readret = await tspi2wb.read(0x10, nbbyte=6)
    await Timer(10, units="us")

    transaction_count = len(tspi2wb.wbm._recvQ)
    assert transaction_count == 1, f"Received {transaction_count}, expected 1"

    for transaction in tspi2wb.wbm._recvQ:
        transaction_len = len(transaction)
        assert transaction_len == 6+1, f"Transaction too short ({transaction_len} expected 7)"
        for t, (addr, val), expvalue in zip(transaction, testvalues, writevalues):
            assert int(t.adr) == addr, "Bad address @0x{:02X}, expected @0x{:02X}".format(t.adr, addr)
            assert int(t.datrd) == expvalue, "Value read 0x{:x} @0x{:02X} should be 0x{:02X}".format(t.datrd, addr, expvalue)

@cocotb.test(skip=not Tone_data_frame)
async def test_write_one_data_frame(dut):
    tspi2wb = TestSpi2Wb(dut)
    if tspi2wb.addr_ext:
        dut._log.info("Address is extended to 15bits")
    await tspi2wb.reset()

    if tspi2wb.datasize == 8:
        #              addr  value
        testvalues = [(0x02, 0xca),
                      (0x10, 0xfe),
                      (0x00, 0x55),
                      (0x7F, 0x12)]
    elif tspi2wb.datasize == 16:
        #              addr  value
        testvalues = [(0x02, 0xcafe),
                      (0x10, 0xfeca),
                      (0x00, 0x5599),
                      (0x7F, 0x1234)]

    for addr, value in testvalues:
        dut._log.info("Writing 0x{:02X} @ 0x{:02X}".format(value, addr))
        await tspi2wb.write(addr, [value])

    transaction_count = len(tspi2wb.wbm._recvQ)
    assert transaction_count == 4, f"Received {transaction_count}, expected 4"

    for transaction, (addr, expvalue) in zip(tspi2wb.wbm._recvQ, testvalues):
        for t in transaction:
            assert int(t.adr) == addr, "Bad address @0x{:02X}, expected @0x{:02X}".format(t.adr, addr)
            assert int(t.datwr) == expvalue, "Value read 0x{:x} @0x{:02X} should be 0x{:02X}".format(t.datwr, addr, expvalue)

@cocotb.test(skip=not Tone_data_frame)
async def test_read_one_data_frame(dut):
    if DATASIZE == "8":
        #              addr  value
        testvalues = [(0x02, 0xca),
                      (0x10, 0xfe),
                      (0x00, 0x55),
                      (0x7F, 0x12)]
    elif DATASIZE == "16":
        #              addr  value
        testvalues = [(0x02, 0xcafe),
                      (0x10, 0xfeca),
                      (0x00, 0x5599),
                      (0x7F, 0x1234)]

    dut._log.info(t[1] for t in testvalues)
    tspi2wb = TestSpi2Wb(dut, wbdatgen=iter(t[1] for t in testvalues))
    await tspi2wb.reset()

    for addr, expvalue in testvalues:
        readval = (await tspi2wb.read(addr))[0]
        assert int(readval) == expvalue, "Value read 0x{:x} @0x{:02X} should be 0x{:02X}".format(readval, addr, expvalue)

    transaction_count = len(tspi2wb.wbm._recvQ)
    assert transaction_count == 4, f"Received {transaction_count}, expected 4"

    for transaction, (addr, expvalue) in zip(tspi2wb.wbm._recvQ, testvalues):
        for t in transaction:
            assert int(t.adr) == addr, "Bad address @0x{:02X}, expected @0x{:02X}".format(t.adr, addr)
            assert int(t.datrd) == expvalue, "Value read 0x{:x} @0x{:02X} should be 0x{:02X}".format(t.datrd, addr, expvalue)
