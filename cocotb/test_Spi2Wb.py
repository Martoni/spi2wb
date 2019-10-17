import os
import cocotb
import logging
from cocotb.triggers import Timer
from cocotb.result import raise_error
from cocotb.result import TestError
from cocotb.result import ReturnValue
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotb.triggers import RisingEdge
from cocotb.triggers import FallingEdge
from cocotb.triggers import ClockCycles

from cocomod.spi import *

DATASIZE = os.environ['DATASIZE']

class SlaveSpi(object):
    INTERFRAME = (100, "ns")

    def __init__(self, dut, clock, cpol=0, cpha=1, datasize=DATASIZE):
        self._dut = dut
        self._cpol = cpol
        self._cpha = cpha
        self.datasize = datasize
        if cpol == 1:
            raise Exception("cpol = 1 not implemented yet")
        if cpha == 0:
            raise Exception("cpha = 0 not implemented yet")
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

    @cocotb.coroutine
    def reset(self):
        self._dut.rstn <= 0
        short_per = Timer(100, units="ns")
        self._dut.rstn <= 0
        self.spimod.set_cs(False)
        self._dut.mosi <= 0
        self._dut.sclk <= 0
        yield short_per
        self._dut.rstn <= 1
        yield short_per

    @cocotb.coroutine
    def writeByte(self, addr, value, datasize=8):
        if not datasize in [8, 16]:
            raise Exception("Size {} not supported".format(datasize))
        sclk_per = Timer(self.spi_config.baudrate[0],
                         units=self.spi_config.baudrate[1])
        self.spimod.set_cs(True)
        yield sclk_per
        yield self.spimod.send(0x80|addr)
        yield Timer(self.INTERFRAME[0], units=self.INTERFRAME[1])
        yield self.spimod.send((value >> 8)&0x00FF)
        yield self.spimod.send(value&0x00FF)
        yield sclk_per
        self.spimod.set_cs(False)
        yield sclk_per
 
    @cocotb.coroutine
    def readByte(self, addr, datasize=8):
        if not datasize in [8, 16]:
            raise Exception("Size {} not supported".format(datasize))
        sclk_per = Timer(self.spi_config.baudrate[0],
                         units=self.spi_config.baudrate[1])
        self.spimod.set_cs(True)
        yield sclk_per
        yield self.spimod.send(addr)
        yield sclk_per
        yield self.spimod.send(0x00)  # let _monitor_recv getting value
        if datasize == 16:
            yield self.spimod.send(0x00)
        yield sclk_per
        self.spimod.set_cs(False)
        ret = yield self.spimod.wait_for_recv(1) # waiting for receive value
        yield sclk_per
        try:
            value_read = int(ret["miso"][-datasize:], 2)
        except ValueError:
            value_read = ret["miso"][-datasize:]
        raise ReturnValue(value_read)


@cocotb.test()
def test_one_data_frame(dut):
    dut._log.info("Launching slavespi test")
    slavespi = SlaveSpi(dut, Clock(dut.clock, 1, "ns"))
    datasize = int(slavespi.datasize)
    dut._log.info("Datasize is {}".format(datasize))
    yield slavespi.reset()
    sclk_per = Timer(10, units="ns")
    short_per = Timer(100, units="ns")
    if(datasize==8):
        #              addr  value
        testvalues = [(0x02, 0xca),
                      (0x10, 0xfe),
                      (0x00, 0x55),
                      (0x7F, 0x12)]
    elif(datasize==16):
        #              addr  value
        testvalues = [(0x02, 0xcafe),
                      (0x10, 0xfeca),
                      (0x00, 0x5599),
                      (0x7F, 0x1234)]

    # Writing values
    for addr, value in testvalues:
        dut._log.info("Write 0x{:02X} @ 0x{:02X}".format(value, addr))
        yield slavespi.writeByte(addr, value, datasize=datasize)

    # Reading back
    for addr, value in testvalues:
        vread = yield slavespi.readByte(addr, datasize=datasize)
        dut._log.info("Read byte 0x{:02X} @ 0x{:02X}".format(vread, addr))
        if vread != value:
            raise TestError("Value read 0x{:02X} @0x{:02X} should be 0x{:02X}"
                    .format(vread, addr, value))
