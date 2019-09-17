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


class SlaveSpi(object):
    INTERFRAME = (100, "ns")

    def __init__(self, dut, clock, cpol=0, cpha=1):
        self._dut = dut
        self._cpol = cpol
        self._cpha = cpha
        if cpol == 1:
            raise Exception("cpol = 1 not implemented yet")
        if cpha == 0:
            raise Exception("cpha = 0 not implemented yet")
        self._clock_thread = cocotb.fork(clock.start())


    @cocotb.coroutine
    def reset(self):
        self._dut.rstn <= 0
        short_per = Timer(100, units="ns")
        self._dut.rstn <= 0
        self._dut.csn <= 1
        self._dut.mosi <= 0
        self._dut.sclk <= 0
        yield short_per
        self._dut.rstn <= 1
        yield short_per
        self._dut.BlinkLed.countReg <= 0x989680 - 10

    @cocotb.coroutine
    def sendReceiveFrame(self, raddr, dataValue=0):
        rvalue = 0
        short_per = Timer(100, units="ns")
        sclk_per = Timer(10, units="ns")
        self._dut.csn <= 0
        self._dut.sclk <= 0
        yield short_per

        # Writing addr
        self._dut._log.info("Writing value 0x{:02X}".format(raddr))
        for i in range(8):
            self._dut.sclk <= 1
            self._dut.mosi <= (raddr >> (7-i)) & 0x01
            yield sclk_per
            self._dut.sclk <= 0
            yield sclk_per

        yield Timer(self.INTERFRAME[0], units=self.INTERFRAME[1])

        # reading/writing value
        for i in range(8):
            yield sclk_per
            self._dut.sclk <= 1
            self._dut.mosi <= (dataValue >> (8-i-1)) & 0x01
            yield sclk_per
            self._dut.sclk <= 0
            rvalue += int(self._dut.miso.value) << (8-i-1)

        self._dut.sclk <= 0
        self._dut.csn <= 0
        yield short_per
        self._dut.csn <= 1
        yield short_per
        self._dut.sclk <= 0
        yield short_per
        raise ReturnValue(rvalue)

    @cocotb.coroutine
    def writeByte(self, addr, value):
        yield self.sendReceiveFrame(0x80|addr, value)

    @cocotb.coroutine
    def readByte(self, addr):
        ret = yield self.sendReceiveFrame(0x7F&addr)
        raise ReturnValue(ret)

@cocotb.test()
def test_one_frame(dut):
    dut._log.info("Launching slavespi test")
    slavespi = SlaveSpi(dut, Clock(dut.clock, 1, "ns"))
    yield slavespi.reset()
    sclk_per = Timer(10, units="ns")
    short_per = Timer(100, units="ns")

    yield slavespi.writeByte(0x02, 0xca)
    yield slavespi.writeByte(0x10, 0xfe)
    vread = yield slavespi.readByte(0x02)
    dut._log.info("Read byte 0x{:02}".format(vread))
    vread = yield slavespi.readByte(0x10)
    dut._log.info("Read byte 0x{:02}".format(vread))

