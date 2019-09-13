package spi2wb

import chisel3._
import chisel3.util._
import chisel3.experimental._
import chisel3.Driver

// minimal signals definition for a wishbone bus 
// (no SEL, no TAG, no pipeline, ...)
class WbMaster (private val dwith: Int, private val awith: Int) extends Bundle {
    val adr_o = Output(UInt(awith.W))
    val dat_i = Input(UInt(dwith.W))
    val dat_o = Output(UInt(dwith.W))
    val we_o = Output(Bool())
    val stb_o = Output(Bool())
    val ack_i = Input(Bool())
    val cyc_o = Output(Bool())
}

class SpiSlave extends Bundle {
    val mosi = Input(Bool())
    val miso = Output(Bool())
    val sclk = Input(Bool())
    val csn = Input(Bool())
}

class Spi2Wb extends Module {
  val io = IO(new Bundle{
    // SPI signals
    val spi = new SpiSlave()
    // Wishbone master output
    val wbm = new WbMaster(8, 7)
  })

  // TODO: wishbone interface
  io.wbm.adr_o := 0.U
  io.wbm.dat_o := 0.U
  io.wbm.we_o := 0.U
  io.wbm.stb_o := 0.U
  io.wbm.cyc_o := 0.U

  // CPOL  | leading edge | trailing edge
  // ------|--------------|--------------
  // false | rising       | falling
  // true  | falling      | rising

  val CPOL = false
  assert(CPOL==false, "Only CPOL==false supported")

  // CPHA  | data change    | data read
  // ------|----------------|--------------
  // false | trailling edge | leading edge
  // true  | leading edge   | trailing edge
  val CPHA = true
  assert(CPHA==true, "Only CPHA==true supported")
  val width = 8
  val count = RegInit("hff".U(width.W))

  def risingedge(x: Bool) = x && !RegNext(x)
  def fallingedge(x: Bool) = !x && RegNext(x)

  val misoReg = RegInit(true.B)
  val mosiReg = RegNext(io.spi.mosi)
  val sclkReg = RegNext(io.spi.sclk)
  val csnReg =  RegNext(io.spi.csn)

  val valueReg = RegInit("hca".U(width.W))
  val readReg =  RegInit("h00".U(width.W))
  val writeReg = RegInit("h00".U(width.W))

  io.spi.miso := misoReg

  when(risingedge(csnReg)) {
    when(count >= width.U) {
      valueReg := writeReg
    }
  }.elsewhen(fallingedge(csnReg)) {
    count := 0.U
    readReg := valueReg
    writeReg := 0.U
  }.elsewhen((count < (2*width).U) && (csnReg === 0.U) ) {
    when(risingedge(sclkReg)) {
      when(count < width.U){
        writeReg := writeReg | Cat(0.U((width-1).W), mosiReg) << count
      }
      count := count + 1.U
    }
    when(fallingedge(sclkReg)) {
      when(count >= width.U) {
        misoReg := readReg(count - width.U)
      }
    }
  }
}

// Blinking module to validate hardware
class BlinkLed extends Module {
  val io = IO(new Bundle{
    val blink = Output(Bool())
  })

  val blinkReg = RegNext(io.blink, false.B)
  io.blink := blinkReg
  val regSize = 24
  val max = "h989680".U

  val countReg = RegInit(0.U(regSize.W))

  countReg := countReg + 1.U
  when(countReg === max) {
    countReg := 0.U
    blinkReg := !blinkReg
  }

}

class TopSpi2Wb extends RawModule {
  // Clock & Reset
  val clock = IO(Input(Clock()))
  val rstn  = IO(Input(Bool()))

  // Blink
  val blink = IO(Output(Bool()))

  // SPI
  val mosi = IO(Input(Bool()))
  val miso = IO(Output(Bool()))
  val sclk = IO(Input(Bool()))
  val csn  = IO(Input(Bool()))

  withClockAndReset(clock, !rstn) {
    // Blink connections
    val blinkModule = Module(new BlinkLed)
    blink := blinkModule.io.blink

    // SPI to wb connections
    val slavespi = Module(new Spi2Wb)
    miso := slavespi.io.spi.miso
    // spi
    slavespi.io.spi.mosi := ShiftRegister(mosi, 2) // ShiftRegister
    slavespi.io.spi.sclk := ShiftRegister(sclk, 2) // used for clock
    slavespi.io.spi.csn  := ShiftRegister(csn, 2)  // synchronisation
    // wb
    slavespi.io.wbm.dat_i := 0.U
    slavespi.io.wbm.ack_i := 0.U
  }
}

object Spi2Wb extends App {
  println("****************************")
  println("* Generate verilog sources *")
  println("****************************")
  println("Virgin module")
  chisel3.Driver.execute(Array[String](), () => new Spi2Wb())
//  println("Real world module with reset inverted")
//  chisel3.Driver.execute(Array[String](), () => new TopSpi2Wb())
}
