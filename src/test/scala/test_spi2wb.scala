package spi2wb

import chisel3._
import chisel3.simulator.EphemeralSimulator._
import org.scalatest.flatspec.AnyFlatSpec


class Spi2WbSpec extends AnyFlatSpec {
  behavior of "Spi2Wb"
  it should "work" in {
    simulate(new Spi2Wb(8, 7)) { c =>
      println("Begin of Spi2Wb")
      for (i <- 1 to 10) {
        c.clock.step(1)
      }
      println("End of Spi2Wb")
    }
  }
}

object TestSpi2Wb extends App {
  org.scalatest.nocolor.run(new Spi2WbSpec)
}
