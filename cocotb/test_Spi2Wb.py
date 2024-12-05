import os
import cocotb
import logging
from cocotb.triggers import Timer
from cocotb.result import raise_error
from cocotb.result import TestError, TestFailure
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotb.triggers import RisingEdge
from cocotb.triggers import FallingEdge
from cocotb.triggers import ClockCycles

from cocotbext.spi import *

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

    def __init__(self, dut, clock, cpol=0, cpha=1,
                 datasize=DATASIZE, addr_ext=EXTADDR,
                 burst=BURST):
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

        if cpol == 1:
            raise NotImplementedError("cpol = 1 not implemented yet")
        if cpha == 0:
            raise NotImplementedError("cpha = 0 not implemented yet")

        self._clock_thread = cocotb.start_soon(clock.start())

        spi_bus = SpiBus.from_entity(dut, cs_name='csn')

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

    async def reset(self):
        self._dut.rstn.value = 0
        short_per = Timer(100, units="ns")
        await short_per
        self._dut.rstn.value = 1
        await short_per

    async def _transfer(self, addr, values=[], write=False, burst=False):

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

        if burst:
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

    async def write_word(self, addr, value):
        return await self._transfer(addr, [value], write=True, burst=False)

    async def read_word(self, addr):
        return (await self._transfer(addr, [0x0], write=False, burst=False))[0]

    async def burst_write(self, addr, lvalues=[]):
        if BURST != "1":
            raise NotImplementedError("BURST synthesis option not set")
        if len(lvalues) < 2:
            raise NotImplementedError("should be at least 2 bytes lenght burst")

        return await self._transfer(addr, lvalues, write=True, burst=True)

    async def burst_read(self, addr, nbByte=10):
        if BURST != "1":
            raise NotImplementedError("BURST synthesis option not set")
        if nbByte < 2:
            raise NotImplementedError("should be at least 2 bytes lenght burst")

        b = []
        for _ in range(nbByte):
            b.append(0x0)

        return await self._transfer(addr, b, write=False)

@cocotb.test(skip=not Tburst_read)
async def test_burst_read(dut):
    test_success =True

    dut._log.info("Launching tspi2wb burst test")
    tspi2wb = TestSpi2Wb(dut, Clock(dut.clock, 1, "ns"))
    if tspi2wb.addr_ext:
        dut._log.info("Address is extended to 14bits")
    await tspi2wb.reset()
    sclk_per = Timer(10, units="ns")
    short_per = Timer(100, units="ns")

    addr = 0x10
    testvalues = [(addr, (0xaa<<8 | addr)) for addr in range(addr,addr + 6)]
    writevalues = [value[-1] for value in testvalues]

    # fill memory with burst
    await tspi2wb.burst_write(addr, writevalues)

    await Timer(50, units="us")

    # read burst
    readret = await tspi2wb.burst_read(0x10, nbByte=6)

    dut._log.info("DEBUG")
    dut._log.info(readret)

    for readval, expval in zip(readret, writevalues):
        assert int(readval) == expval, "Value read 0x{:x} @0x{:02X} should be 0x{:02X}".format(readval, addr, expvalue)

@cocotb.test(skip=not Tone_data_frame)
async def test_one_data_frame(dut):
    test_success = True
    test_msg = []
    dut._log.info("Launching tspi2wb test")
    tspi2wb = TestSpi2Wb(dut, Clock(dut.clock, 1, "ns"))
    await Timer(10, 'us')
    if tspi2wb.addr_ext:
        dut._log.info("Address is extended to 15bits")
    await tspi2wb.reset()

    sclk_per = Timer(10, units="ns")
    short_per = Timer(100, units="ns")
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

    # Writing values
    for addr, value in testvalues:
        dut._log.info("Writing 0x{:02X} @ 0x{:02X}".format(value, addr))
        await tspi2wb.write_word(addr, value)

    # Reading back
    for addr, expvalue in testvalues:
        readval = await tspi2wb.read_word(addr)
        assert int(readval) == expvalue, "Value read 0x{:x} @0x{:02X} should be 0x{:02X}".format(readval, addr, expvalue)
