# Cocotb testbench

This file describe directives to install and use cocotb

## Cocotb

Cocotb is a python module that can be installed with pip :
```
$ python -m pip install cocotb
```

Version 1.2 of cocotb as been used here, with python 3.7.

## cocotbext-spi

cocotbext-spi is a cocotb extension used to test spi. It could be found in
following url :
https://github.com/Martoni/cocotbext-spi

To install it, it can be symply cloned and installed locally :
```
$ git clone https://github.com/Martoni/cocotbext-spi
$ cd cocotbext-spi
$ python -m pip install -e .
```

# Launching the bench

Parameter should be passed to makefile for the datasize used :

```
# 16 bits data extended address and burst mode
$ DATASIZE=16 EXTADDR=1 BURST=1 make
# 8 bits data simple address and no burst
$ DATASIZE=8 EXTADDR=0 BURST=0 make
```

# Cleaning

To be sure that all files are reconstructed do :

```
$ make mrproper
```
