VIEW?=gtkwave
SIM?=icarus
COCOTBVERILOGDIR?=../

export COCOTB_REDUCED_LOG_FMT=1

TOPLEVEL=Spi2Wb
VERILOG_SOURCES = $(COCOTBVERILOGDIR)/$(TOPLEVEL).sv
MODULE=test_Spi2Wb

ifeq ($(SIM),verilator)
EXTRA_ARGS += --trace --trace-structs
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

all: res

res: results.xml
	@if grep -Eq "<failure .+ \/>" results.xml; then exit 1; fi

view:
	$(VIEW) -a spi2wb.gtkw

mrproper:
	-rm $(TOPLEVEL).vcd
	-rm dump.vcd
	-rm -rf sim_test-spi2wb*
	-rm -rf build
	-rm results.xml
	-rm *.pyc
	-rm -rf __pycache__
