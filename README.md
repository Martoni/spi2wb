# spi2wb
Drive a Wishbone master bus with an SPI bus.

## Install instructions

This component use Chisel3 as HDL and Cocotb for testbench framework.
There is a hack with cocotbify that require a git submodule. Then to clone it
don't forget the recursive option :
```
$ git clone --recurse-submodules https://github.com/Martoni/spi2wb.git
```

## Simulation instructions

To simulate the module go to cocotb/ directory then do make :
```
$ make
```

To see waveform use gtkwave with following commande :
```
$ gtkwave TopSpi2Wb.vcd
```
