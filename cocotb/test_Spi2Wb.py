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


class TestSpi2Wb(object):
    INTERFRAME = (100, "ns")

    def __init__(self, dut, clock, cpol=0, cpha=1,
                 datasize=DATASIZE, addr_ext=EXTADDR):
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
        self.datasize = datasize
        if cpol == 1:
            raise NotImplementedError("cpol = 1 not implemented yet")
        if cpha == 0:
            raise NotImplementedError("cpha = 0 not implemented yet")
        self._clock_thread = cocotb.fork(clock.start())

        spi_sigs = SPISignals(miso=dut.miso,
                              mosi=dut.mosi,
                              sclk=dut.sclk,
                              cs=dut.csn)

        self.spi_config = SPIConfig(cpol=False,
                                    cpha=True,
                                    baudrate=(1, "us"),
                                    csphase=False)

        self.spimod = SPIModule(self.spi_config, spi_sigs, clock)

    async def reset(self):
        self._dut.rstn <= 0
        short_per = Timer(100, units="ns")
        self._dut.rstn <= 0
        self.spimod.set_cs(False)
        self._dut.mosi <= 0
        self._dut.sclk <= 0
        await short_per
        self._dut.rstn <= 1
        await short_per

    async def write_byte(self, addr, value, datasize=8):
        if not datasize in [8, 16]:
            raise NotImplementedError("Size {} not supported".format(datasize))
        sclk_per = Timer(self.spi_config.baudrate[0],
                         units=self.spi_config.baudrate[1])
        self.spimod.set_cs(True)
        await sclk_per
        if not self.addr_ext:
            await self.spimod.send(0x80|addr)
        else:
            await self.spimod.send(0x80|((addr >> 8)&0xFF))
            await self.spimod.send(addr&0xFF)
        await Timer(self.INTERFRAME[0], units=self.INTERFRAME[1])
        if datasize == 16:
            await self.spimod.send((value >> 8)&0x00FF)
        await self.spimod.send(value&0x00FF)
        await sclk_per
        self.spimod.set_cs(False)
        await sclk_per
 
    async def read_byte(self, addr, datasize=8):
        if not datasize in [8, 16]:
            raise NotImplementedError("Size {} not supported".format(datasize))
        sclk_per = Timer(self.spi_config.baudrate[0],
                         units=self.spi_config.baudrate[1])
        self.spimod.set_cs(True)
        await sclk_per
        if not self.addr_ext:
            await self.spimod.send(addr)
        else:
            await self.spimod.send((addr>>8)&0xFF)
            await self.spimod.send(addr&0xFF)
        await sclk_per
        await self.spimod.send(0x00)  # let _monitor_recv getting value
        if datasize == 16:
            await self.spimod.send(0x00)
        await sclk_per
        self.spimod.set_cs(False)
        ret = await self.spimod.wait_for_recv(1) # waiting for receive value
        await sclk_per
        try:
            value_read = int(ret["miso"][-datasize:], 2)
        except ValueError:
            value_read = ret["miso"][-datasize:]

        return value_read


@cocotb.test()
async def test_one_data_frame(dut):
    test_success = True
    test_msg = []
    dut._log.info("Launching tspi2wb test")
    tspi2wb = TestSpi2Wb(dut, Clock(dut.clock, 1, "ns"))
    datasize = int(tspi2wb.datasize)
    if tspi2wb.addr_ext:
        dut._log.info("Address is extended to 15bits")
    dut._log.info("Datasize is {}".format(datasize))
    await tspi2wb.reset()
    sclk_per = Timer(10, units="ns")
    short_per = Timer(100, units="ns")
    if datasize == 8:
        #              addr  value
        testvalues = [(0x02, 0xca),
                      (0x10, 0xfe),
                      (0x00, 0x55),
                      (0x7F, 0x12)]
    elif datasize == 16:
        #              addr  value
        testvalues = [(0x02, 0xcafe),
                      (0x10, 0xfeca),
                      (0x00, 0x5599),
                      (0x7F, 0x1234)]

    # Writing values
    for addr, value in testvalues:
        dut._log.info("Writing 0x{:02X} @ 0x{:02X}".format(value, addr))
        await tspi2wb.write_byte(addr, value, datasize=datasize)

    # Reading back
    for addr, value in testvalues:
        vread = await tspi2wb.read_byte(addr, datasize=datasize)
        dut._log.info("Read byte 0x{:x} @ 0x{:02X} (should be 0x{:02X})"
                .format(vread, addr, value))
        if int(vread) != value:
            msg = ("Value read 0x{:x} @0x{:02X} should be 0x{:02X}"
                    .format(vread, addr, value))
            dut._log.error(msg)
            test_msg.append(msg)
            test_success = False

    if not test_success:
        raise TestFailure("\n".join(test_msg))

