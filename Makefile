SBT=sbt

ifeq ($(EXTADDR), 1)
	EXT=Ext
else
	EXT=
endif

hdl:
	$(SBT) "runMain spi2wb.Spi2Wb$(EXT)$(DATASIZE)"

test:
	cd cocotb/; DATASIZE=$(DATASIZE) EXTADDR=$(EXTADDR) make

scalatest:
	$(SBT) "test:testOnly spi2wb.TestSpi2Wb"

publishlocal:
	$(SBT) publishLocal

mrproper:
	make -C cocotb/ mrproper
	-rm *.anno.json
	-rm *.fir
	-rm *.v
	-rm -rf target
	-rm -rf test_run_dir
	-rm -rf project
