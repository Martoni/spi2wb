#! /usr/bin/python3
# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Author:   Fabien Marteau <fabien.marteau@armadeus.com>
# Created:  17/09/2019
#-----------------------------------------------------------------------------
#  Copyright (2019)  Armadeus Systems
#  Testing spi2wb with bus pirate.
#  To be functionnal, pyBusPirate from Martoni github should be installed
#  in /opt :
#  ```
#  $ cd /opt/; git clone https://github.com/Martoni/pyBusPirate.git 
#-----------------------------------------------------------------------------
""" test_bus_pirate
"""

import sys
from serial.serialutil import SerialException
sys.path.append("/opt/pyBusPirate/")
from pyBusPirateLite.SPI import *

class VbusPirateError(Exception):
    pass

class VbusPirate(object):
    """
    """
    UART_DEVNAME = "/dev/ttyACM0"
    UART_SPEED = 115200
    SPI_SPEED = SPISpeed._1MHZ
    #SPICfg.CLK_EDGE |
    SPI_CFG = SPICfg.OUT_TYPE
    PINS_CFG = PinCfg.POWER | PinCfg.CS | PinCfg.AUX

    def __init__(self, devname=UART_DEVNAME, speed=UART_SPEED):
        self.spi = SPI(devname, speed)
        if not self.spi.BBmode():
            raise VbusPirateError("Can't enter to binmode")
        if not self.spi.enter_SPI():
            raise VbusPirateError("Can't enter raw SPI mode")
        if not self.spi.set_speed(self.SPI_SPEED):
            raise VbusPirateError("Can't Configure SPI speed")
        if not self.spi.cfg_spi(self.SPI_CFG):
            raise VbusPirateError("Can't Configure SPI configuration")
        if not self.spi.cfg_pins(self.PINS_CFG):
            raise VbusPirateError("Can't Configure SPI peripherals")
        self.spi.timeout(0.2)

    def sendReceiveFrame(self, raddr, dataValue=0):
        vbp.spi.CS_Low()
        resp = vbp.spi.bulk_trans([raddr])
        # Wait little bit
        resp = vbp.spi.bulk_trans([dataValue])
        vbp.spi.CS_High()
        if type(resp) != bytes:
            resp = ord(resp[-1])
        else:
            resp = ord(resp)
        return resp

    def writeByte(self, addr, value):
        self.sendReceiveFrame(0x80|addr, value)

    def readByte(self, addr):
        ret = self.sendReceiveFrame(0x7F&addr)
        return ret


if __name__ == "__main__":
    """ Testing spi2wb with buspirate"""
    if sys.version_info[0] < 3:
        raise Exception("Must be using Python 3")

    vbp = VbusPirate()
    #              addr  value
    testvalues = [(0x02, 0xca),
                  (0x10, 0xfe),
                  (0x00, 0x55),
                  (0xFF, 0x12)]
    # Writing values
    for addr, value in testvalues:
        print("Write byte 0x{:02X} @ 0x{:02X}".format(value, addr))
        vbp.writeByte(addr, value)
    # Reading back
    for addr, value in testvalues:
        vread = vbp.readByte(addr)
        print("Read byte 0x{:02X} @ 0x{:02X}".format(vread, addr))
        if vread != value:
            raise Exception("Value read 0x{:02X} @0x{:02X} should be 0x{:02X}"
                    .format(vread, addr, value))
