SBT = sbt

hdl:
	$(SBT) "runMain spi2wb.Spi2Wb"

test:
	$(SBT) "test:runMain spi2wb.TestTopSpi2Wb"
