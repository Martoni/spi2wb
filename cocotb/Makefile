VIEW=gtkwave
SIM=icarus
export COCOTB_REDUCED_LOG_FMT=1
TOPLEVEL=TopSpi2Wb
VERILOG_SOURCES = $(PWD)/../$(TOPLEVEL).sv
MODULE=test_Spi2Wb


include $(shell cocotb-config --makefiles)/Makefile.sim

$(PWD)/../$(TOPLEVEL).sv: $(PWD)/../src/main/scala/spi2wb/spi2wb.scala
	echo "datasize "$(DATASIZE)
	cd $(PWD)/../;DATASIZE=$(DATASIZE) EXTADDR=$(EXTADDR) BURST=$(BURST) make

view:
	$(VIEW) -a spi2wb.gtkw

mrproper:
	-rm $(PWD)/../$(TOPLEVEL).sv
	-rm $(TOPLEVEL).vcd
	-rm -rf sim_build
	-rm -rf build
	-rm results.xml
	-rm *.pyc
