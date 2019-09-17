package spi2wb

import chisel3._
import chisel3.experimental.{RawModule, MultiIOModule}
import chisel3.iotesters.PeekPokeTester


class TestSpi2WbMem (dut: Spi2WbMem) extends PeekPokeTester(dut) {
  println("Begin of Spi2WbMem")
  for (i <- 1 to 10) {
    step(1)
  }
  println("End of Spi2WbMem")
}

object TestTopSpi2Wb extends App {

  chisel3.iotesters.Driver(() => new Spi2WbMem(8, 7))
    { c => new TestSpi2WbMem(c)}
}
