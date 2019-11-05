package spi2wb

import chisel3._
import chisel3.iotesters.PeekPokeTester


class TestSpi2Wb (dut: Spi2Wb) extends PeekPokeTester(dut) {
  println("Begin of Spi2Wb")
  for (i <- 1 to 10) {
    step(1)
  }
  println("End of Spi2Wb")
}

object TestSpi2Wb extends App {

  chisel3.iotesters.Driver(() => new Spi2Wb(8, 7))
    { c => new TestSpi2Wb(c)}
}
