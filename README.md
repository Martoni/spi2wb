# spi2wb
Drive a Wishbone master bus with an SPI bus.

## Protocol

The [SPI configuration](https://en.wikipedia.org/wiki/Serial_Peripheral_Interface#Clock_polarity_and_phase) is following :
- Mode b01 ->
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

### Extended address mode

For 16bits data mode frames are following.

- Write frame:
```ascii
MOSI: 1AAAAAAA AAAAAAAA DDDDDDDDDDDDDDDD
MISO: ZZZZZZZZ ZZZZZZZZ ZZZZZZZZZZZZZZZZ
```
- Read frame
```ascii
MOSI : 0AAAAAAA AAAAAAAA ZZZZZZZZZZZZZZZZ
MISO : ZZZZZZZZ ZZZZZZZZ DDDDDDDDDDDDDDDD
```

And with following :
- 1/0: write/read bit
- AAAAAAA: 7 bits address MSB
- AAAAAAAA: 8 bits address LSB
- DDDDDDDDDDDDDD: 16 bits data
- ZZZZZZZZZZZZZZ: Don't care signal

### Burst mode

To use burst mode, spi2wb must be synthetised with the option `aburst=true`.
Then for 16bits data mode and extended address mode it frame are following :

- Write burst frame:
```ascii
# Simple mode:
MOSI: 10AAAAAA AAAAAAAA DDDDDDDDDDDDDDDD
MISO: ZZZZZZZZ ZZZZZZZZ ZZZZZZZZZZZZZZZZ
# Burst mode:
MOSI: 11AAAAAA AAAAAAAA DDDDDDDDDDDDDDDD DDDDDDDDDDDDDDDD DDDDDDDDDDDDDDDD ...
MISO: ZZZZZZZZ ZZZZZZZZ ZZZZZZZZZZZZZZZZ ZZZZZZZZZZZZZZZZ ZZZZZZZZZZZZZZZZ Z.Z
```
- Read frame
```ascii
# Simple mode:
MOSI : 00AAAAAA AAAAAAAA ZZZZZZZZZZZZZZZZ
MISO : ZZZZZZZZ ZZZZZZZZ DDDDDDDDDDDDDDDD
# Burst mode:
MOSI : 01AAAAAA AAAAAAAA ZZZZZZZZZZZZZZZZ ZZZZZZZZZZZZZZZZ ZZZZZZZZZZZZZZZZ ...
MISO : ZZZZZZZZ ZZZZZZZZ DDDDDDDDDDDDDDDD DDDDDDDDDDDDDDDD DDDDDDDDDDDDDDDD Z.Z
```

With following :
- First 1/0: write/read bit
- Second 1/0: burst/simple
- AAAAAAA: 6 bits address MSB
- AAAAAAAA: 8 bits address LSB
- DDDDDDDDDDDDDD: 16 bits data
- ZZZZZZZZZZZZZZ: Don't care signal

In burst mode, wishbone word address will be increased by 1 each word
read/write if `burst_auto_incr` is set to `true`.

## Install instructions

This component use Chisel3 as HDL and Cocotb for testbench framework.

First of all, some dependancies should be installed : 

**WbPlumbing**:

[WbPlumbing](https://github.com/Martoni/WbPlumbing) is a chisel library
that do Wishbone connections. It should be published locally :

```
$ git clone https://github.com/Martoni/WbPlumbing.git
$ cd WbPlumbing
$ sbt "publishLocal"
```

**CocoTB**

For cocotb simulation instruction see the [readme](https://github.com/Martoni/spi2wb/blob/master/cocotb/README.md).


## Simulation instructions

### iotesters

A minimal code has been written in *src/test/scala* to test the component in scala. To launch it simply use make:
```shell
$ make scalatest
```
But the actual testbench is written with Python Cocotb module.

### Cocotb

- For all testbenches do:
```shell
$ make test
```
- For 8 bits datasize do:
```shell
$ make test-spi2wb8
```
- For 16 bits datasize do:
```shell
$ make test-spi2wb16
```
- For 16 bits datasize with extended address do:
```shell
$ make test-spi2wbext16
```
- For 16 bits datasize with extended address and burst do:
```shell
$ make test-spi2wbext16burst
```

To see waveform use gtkwave with following command :
```
$ gtkwave cocotb/TopSpi2Wb.vcd
```
## Test hardware

### Generate verilog

To generate verilog synthesizable component do :
```shell
$ make
```

This will generate a verilog top components named ```TopSpi2Wb.v```. This
component include a blinker to unsure that the bitstream is well downloaded and
fpga started.

### Testing with busPirate

The design has been tested with a
[busPirate](https://sandboxelectronics.com/?product=bus-pirate-v4-universal-interface-gadget).
A python script is available in hwtest/ directory to test the component with
buspirate :

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
Write byte 0xCAFE @ 0x02
Write byte 0x5958 @ 0x01
Write byte 0x5599 @ 0x00
Write byte 0xBAAF @ 0x10
Write byte 0x1234 @ 0x12
Read byte 0xCAFE @ 0x02
Read byte 0x5958 @ 0x01
Read byte 0x5599 @ 0x00
Read byte 0xBAAF @ 0x10
Read byte 0x1234 @ 0x12
```
