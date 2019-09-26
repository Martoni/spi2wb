#! /usr/bin/python3
# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Author:   Fabien Marteau <fabien.marteau@armadeus.com>
# Created:  17/09/2019
#-----------------------------------------------------------------------------
#  Copyright (2019)  Armadeus Systems
#  Testing spi2wb with bus pirate.
#  To be functionnal, pyBusPirate from Martoni github should be installed
#  in /opt :
#  ```
#  $ cd /opt/; git clone https://github.com/Martoni/pyBusPirate.git 
#-----------------------------------------------------------------------------
""" test_bus_pirate
"""

import sys
import time
import getopt
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

    def __init__(self, devname=UART_DEVNAME, speed=UART_SPEED, datasize=8):
        self._datasize=datasize
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
        # Then
        if(self._datasize == 8):
            resp = vbp.spi.bulk_trans([dataValue])
        else:
            resp = vbp.spi.bulk_trans([dataValue>>8, dataValue&0x00FF])
        vbp.spi.CS_High()
        if type(resp) != bytes and len(resp) != 2:
            resp = ord(resp[-1])
        elif(len(resp) == 2):
            if(type(resp) == str):
                resp = (ord(resp[0])<<8) + ord(resp[1])
            else:
                resp = (resp[0]<<8) + resp[1]
        else:
            resp = ord(resp)
        return resp

    def writeByte(self, addr, value):
        self.sendReceiveFrame(0x80|addr, value)

    def readByte(self, addr):
        ret = self.sendReceiveFrame(0x7F&addr)
        return ret

def usage():
    """ Print usages """
    print("Usage :")
    print("$ python3 test_bus_pirate.py [options]")
    print("-h, --help             print this help message")
    print("-d, --datasize [size]  set datasize [8,16]")


if __name__ == "__main__":
    """ Testing spi2wb with buspirate"""
    if sys.version_info[0] < 3:
        raise Exception("Must be using Python 3")

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hd:",
                                   ["help", "datasize="])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)

    datasize = 8
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-d", "--datasize"):
            datasize = int(arg)

    vbp = VbusPirate(datasize=datasize)
    if(datasize == 8):
        #              addr  value8
        testvalues = [(0x02, 0xca),
                      (0x10, 0xfe),
                      (0x00, 0x55),
                      (0x7F, 0x12)]
    elif(datasize == 16):
        #              addr  value16
        testvalues = [(0x02, 0xcafe),
                      (0x01, 0x5958),
                      (0x00, 0x5599),
                      (0x10, 0xbaaf),
                      (0x12, 0x1234)
                      ]
    else:
        raise Exception("{} datasize not supported".format(datasize))

    # all values :
    #testvalues = [(v, ((v<<8) + v)) for v in range(128)]

    # Writing values
    for addr, value in testvalues:
        if datasize == 8:
            print("Write byte 0x{:02X} @ 0x{:02X}".format(value, addr))
        else:
            print("Write byte 0x{:04X} @ 0x{:02X}".format(value, addr))
        vbp.writeByte(addr, value)
    # Reading back
    for addr, value in testvalues:
        vread = vbp.readByte(addr)
        if datasize == 8:
            print("Read byte 0x{:02X} @ 0x{:02X}".format(vread, addr))
        else:
            print("Read byte 0x{:04X} @ 0x{:02X}".format(vread, addr))

        if vread != value:
            raise Exception("Value read 0x{:04X} @0x{:02X} should be 0x{:04X}"
                    .format(vread, addr, value))
