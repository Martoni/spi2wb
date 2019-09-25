# spi2wb
Drive a Wishbone master bus with an SPI bus.

## Protocol

The [SPI configuration](https://en.wikipedia.org/wiki/Serial_Peripheral_Interface#Clock_polarity_and_phase) is following :
- CPOL = 0
- CPHA = 1
- CS = active low

An spi2wb frame is composed as following :

### 8 bits mode

- Write frame:
```ascii
MOSI : 1AAAAAAA DDDDDDDD
MISO : ZZZZZZZZ ZZZZZZZZ
```
- Read frame
```ascii
MOSI : 0AAAAAAA ZZZZZZZZ
MISO : ZZZZZZZZ DDDDDDDD
```
 And with following :
- 1/0: write/read bit
- AAAAAAA: 7 bits address
- DDDDDDD: 8 bits data
- ZZZZZZZ: Don't care signal


### 16 bits mode

- Write frame:
```ascii
MOSI : 1AAAAAAA DDDDDDDDDDDDDDDD
MISO : ZZZZZZZZ ZZZZZZZZZZZZZZZZ
```
- Read frame
```ascii
MOSI : 0AAAAAAA ZZZZZZZZZZZZZZZZ
MISO : ZZZZZZZZ DDDDDDDDDDDDDDDD
```
 And with following :
- 1/0: write/read bit
- AAAAAAA: 7 bits address
- DDDDDDDDDDDDDD: 16 bits data
- ZZZZZZZZZZZZZZ: Don't care signal

## Install instructions

This component use Chisel3 as HDL and Cocotb for testbench framework.
There is a hack with cocotbify that require a git submodule. Then to clone it
don't forget the recursive option :
```
$ git clone --recurse-submodules https://github.com/Martoni/spi2wb.git
```

## Simulation instructions

### iotesters

A minimal code has been written in *src/test/scala* to test the component in scala. To launch it simply use make:
```shell
$ make test
```
But the actual testbench is written with Python Cocotb module.

### Cocotb

To simulate the module go to cocotb/ directory:
- For 8 bits datasize do:
```shell
$ cd cocotb
$ DATAZISE=8 make
```
- For 16 bits datasize do:
```shell
$ cd cocotb
$ DATAZISE=16 make
```

To see waveform use gtkwave with following command :
```
$ gtkwave TopSpi2Wb.vcd
```
## Test hardware

### Generate verilog

To generate verilog synthesizable component do :
```shell
$ make
```

This will generate a verilog top components named ```TopSpi2Wb.v```. This component include a blinker to unsure that the bitstream is well downloaded and fpga started.

### Testing with busPirate

The design has been tested with a [busPirate](https://sandboxelectronics.com/?product=bus-pirate-v4-universal-interface-gadget).
A python script is available in hwtest/ directory to test the component with buspirate :
- For 8 bits read/write:
```shell
$  python3 test_bus_pirate.py -d8
Write byte 0xCA @ 0x02
Write byte 0xFE @ 0x10
Write byte 0x55 @ 0x00
Write byte 0x12 @ 0xFF
Read byte 0xCA @ 0x02
Read byte 0xFE @ 0x10
Read byte 0x55 @ 0x00
Read byte 0x12 @ 0xFF
```

- For 16 bits read/write:

```shell
$  python3 test_bus_pirate.py -d16
<TO BE TESTED>
```
