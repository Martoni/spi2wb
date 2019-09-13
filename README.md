# spi2wb
Drive a Wishbone master bus with an SPI bus.

## Install instructions

This component use Chisel3 as HDL and Cocotb for testbench framework.
There is a hack with cocotbify that require a git submodule. Then to clone it
don't forget the recursive option :
```
$ git clone --recurse-submodules https://github.com/Martoni/spi2wb.git
```
