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
    def sendReceiveFrame(self, sendValue):
        value = sendValue
        rvalue = 0
        short_per = Timer(100, units="ns")
        sclk_per = Timer(10, units="ns")
        self._dut.csn <= 0
        self._dut.sclk <= 0
        yield short_per
        self._dut._log.info("Writing value 0x{:02X}".format(value))
        # Writing value
        for i in range(8):
            self._dut.sclk <= 1
            self._dut.mosi <= (value >> i) & 0x01
            yield sclk_per
            self._dut.sclk <= 0
            yield sclk_per

        # reading value
        for i in range(8):
            yield sclk_per
            self._dut.sclk <= 1
            yield sclk_per
            self._dut.sclk <= 0
            rvalue += int(self._dut.miso.value) << i

        self._dut.sclk <= 0
        self._dut.csn <= 0
        yield short_per
        self._dut.csn <= 1
        yield short_per
        self._dut.sclk <= 0
        yield short_per
        raise ReturnValue(rvalue)


@cocotb.test()
def test_one_frame(dut):
    dut._log.info("Launching slavespi test")
    slavespi = SlaveSpi(dut, Clock(dut.clock, 1, "ns"))
    yield slavespi.reset()
    sclk_per = Timer(10, units="ns")
    short_per = Timer(100, units="ns")
    value = int("01010101", 2)
    rvalue = yield slavespi.sendReceiveFrame(value)
    for i in range(10):
        yield short_per
    dut._log.info("Read value is 0x{:02x}".format(rvalue))
    oldvalue = value
    value = int("10101010", 2)
    rvalue = yield slavespi.sendReceiveFrame(value)
    if rvalue != oldvalue:
        raise TestError("rvalue is 0x{:02X} and should be 0x{:02X}"
                .format(rvalue, oldvalue))
    dut._log.info("Read value is 0x{:02x}".format(rvalue))
    oldvalue = value
    value = int("11110000", 2)
    rvalue = yield slavespi.sendReceiveFrame(value)
    if rvalue != oldvalue:
        raise TestError("rvalue is 0x{:02X} and should be 0x{:02X}"
                .format(rvalue, oldvalue))
    dut._log.info("Read value is 0x{:02x}".format(rvalue))

