VIEW=gtkwave
SIM=icarus
export COCOTB_REDUCED_LOG_FMT=1
TOPLEVEL=TopSpi2Wb
VERILOG_SOURCES = $(PWD)/$(TOPLEVEL)Cocotb.v
MODULE=test_Spi2Wb
include $(COCOTB)/makefiles/Makefile.inc
include $(COCOTB)/makefiles/Makefile.sim

$(PWD)/$(TOPLEVEL)Cocotb.v: $(PWD)/../$(TOPLEVEL).v
	python cocotbify/cocotbify.py -v $(PWD)/../$(TOPLEVEL).v -o $(PWD)/$(TOPLEVEL)Cocotb.v

$(PWD)/../$(TOPLEVEL).v: $(PWD)/../src/main/scala/spi2wb.scala
	cd $(PWD)/../; make

view: 
	$(VIEW) -a spi2wb.gtkw

mrproper:
	-rm $(PWD)/../$(TOPLEVEL).v
	-rm $(PWD)/$(TOPLEVEL)Cocotb.v
	-rm $(TOPLEVEL).vcd
	-rm -rf sim_build
	-rm -rf build
	-rm results.xml
	-rm *.pyc
