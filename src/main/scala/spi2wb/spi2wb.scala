package spi2wb

import chisel3._
import chisel3.util._
import chisel3.stage.{ChiselStage, ChiselGeneratorAnnotation}

import wbplumbing.WbMaster

class SpiSlave extends Bundle {
    val mosi = Input(Bool())
    val miso = Output(Bool())
    val sclk = Input(Bool())
    val csn = Input(Bool())
}

/**
 * Generate read/write wishbone access driven by spi protocol
 */
class Spi2Wb (dwidth: Int, awidth: Int,
              aburst: Boolean = false,
              addr_ext: Boolean = false) extends Module {
  val io = IO(new Bundle{
    // Wishbone master output
    val wbm = new WbMaster(dwidth, awidth)
    // SPI signals
    val spi = new SpiSlave()
  })

  println("Generate SPI for :")
  println(" - data size : " + dwidth)
  println(" - Addr size : " + awidth)
  println(" - ext addr : " + addr_ext)
  println(" - burst : " + aburst)

  assert(dwidth == 8 || dwidth == 16,
    "Only 8bits or 16bits data supported")

  val spiAddressWith  = (addr_ext, aburst) match {
          case (true, false) => {
              assert(awidth <= 15,
                 "Maximum 15 bits address actually supported")
                 15}
          case (true, true) => {
              assert(awidth <= 14,
                "Maximum 14 bits address actually supported (burst)")
                14}
          case (false, false) => {
              assert(awidth <= 7,
                "Maximum 7 bits address actually supported")
                7}
          case (false, true) => {
              assert(awidth <= 6,
                "Maximum 6 bits address actually supported (burst)")
              6}
  }

  // Wishbone init
  val wbWeReg  = RegInit(false.B)
  val wbStbReg = RegInit(false.B)
  val wbCycReg = RegInit(false.B)

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

  def risingedge(x: Bool) = x && !RegNext(x)
  def fallingedge(x: Bool) = !x && RegNext(x)

  val misoReg = RegInit(true.B)
  val sclkReg = RegNext(io.spi.sclk)
  val csnReg =  RegNext(io.spi.csn)

  val dataReg  = RegInit("h00".U(dwidth.W))
  val addrReg  = RegInit("h00".U(awidth.W))

  val wrReg  = RegInit(false.B)
  val wbFlag = RegInit(false.B)

  val count = RegInit(0.U(dwidth.W))
  //   000    001     010     011        100     101            110
  val sinit::swrreg::saddr::sdataread::swbread::sdatawrite::swbwrite::Nil=Enum(7)
  val stateReg = RegInit(sinit)

  switch(stateReg) {
    is(sinit){
      wrReg := false.B
      count := 0.U
      addrReg := 0.U
      dataReg := 0.U
      misoReg := true.B
      wbWeReg  := false.B
      wbStbReg := false.B
      wbCycReg := false.B
      when(fallingedge(csnReg)){
        stateReg := swrreg
      }
    }
    is(swrreg){
      when(fallingedge(sclkReg)){
        wrReg := io.spi.mosi
        count := 1.U
        stateReg := saddr
      }
    }
    is(saddr){
      when(fallingedge(sclkReg)){
        addrReg := addrReg(awidth - 1, 0) ## io.spi.mosi
        count := count + 1.U
        when(count >= spiAddressWith.U) {
          when(wrReg){
            stateReg := sdatawrite
          }
          when(!wrReg){
            wbWeReg  := false.B
            wbStbReg := true.B
            wbCycReg := true.B
            stateReg := swbread
          }
        }
      }
    }
    is(swbread){
      when(io.wbm.ack_i){
        wbStbReg := false.B
        wbCycReg := false.B
        dataReg  := io.wbm.dat_i
        stateReg := sdataread
      }
    }
    is(sdataread){
      when(risingedge(sclkReg)){
        misoReg := dataReg((spiAddressWith + dwidth).U - count)
        count := count + 1.U
      }
      when(count >= (2 + spiAddressWith + dwidth).U){
        stateReg := sinit
      }
    }
    is(sdatawrite){
      when(fallingedge(sclkReg)){
        dataReg := dataReg(dwidth-2, 0) ## io.spi.mosi
        count := count + 1.U
      }
      when(count >= (1 + spiAddressWith + dwidth).U){
        stateReg := swbwrite
      }
    }
    is(swbwrite){
        wbWeReg  := true.B
        wbStbReg := true.B
        wbCycReg := true.B
        when(io.wbm.ack_i){
          wbWeReg  := false.B
          wbStbReg := false.B
          wbCycReg := false.B
          stateReg := sinit
        }
    }
  }
  // reset state machine to sinit when csn rise
  // even if count is not right
  when(risingedge(csnReg)){
        stateReg := sinit
  }

  // spi signals
  io.spi.miso := misoReg
  // wishbone signals
  io.wbm.adr_o := addrReg
  io.wbm.dat_o := dataReg
  io.wbm.we_o  := wbWeReg
  io.wbm.stb_o := wbStbReg
  io.wbm.cyc_o := wbCycReg
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

// Testing Spi2Wb with a memory connexion
// and reset inverted
class TopSpi2Wb (val dwidth: Int,
                 val aburst: Boolean = false,
                 val extaddr: Boolean = false) extends RawModule {
  // Clock & Reset
  val clock = IO(Input(Clock()))
  val rstn  = IO(Input(Bool()))

  // Simple blink
  val blink = IO(Output(Bool()))

  // SPI
  val mosi = IO(Input(Bool()))
  val miso = IO(Output(Bool()))
  val sclk = IO(Input(Bool()))
  val csn  = IO(Input(Bool()))
  
  val awidth = (extaddr, aburst) match {
          case (true,    false) => 15
          case (true,    true) => 14
          case (false,   false) => 7
          case (false,   true) => 6}

  withClockAndReset(clock, !rstn) {
    // Blink connections
    val blinkModule = Module(new BlinkLed)
    blink := blinkModule.io.blink

    // SPI to wb connections
    val slavespi = Module(new Spi2Wb(dwidth=dwidth,
                                     awidth=awidth,
                                     aburst=aburst,
                                     addr_ext=extaddr))
    miso := slavespi.io.spi.miso
    // spi
    slavespi.io.spi.mosi := ShiftRegister(mosi, 2) // ShiftRegister
    slavespi.io.spi.sclk := ShiftRegister(sclk, 2) // used for clock
    slavespi.io.spi.csn  := ShiftRegister(csn, 2)  // synchronisation

    // wb memory connexion
    val wmem = SyncReadMem(1 << awidth, UInt(dwidth.W))

    slavespi.io.wbm.ack_i := false.B
    when(slavespi.io.wbm.stb_o && slavespi.io.wbm.cyc_o) {
      when(slavespi.io.wbm.we_o){
        // Write memory
        wmem.write(slavespi.io.wbm.adr_o, slavespi.io.wbm.dat_o)
      }
      // read memory
    }
    slavespi.io.wbm.ack_i := RegNext(slavespi.io.wbm.stb_o && slavespi.io.wbm.cyc_o) &&
                                    (slavespi.io.wbm.stb_o && slavespi.io.wbm.cyc_o)
    slavespi.io.wbm.dat_i := wmem.read(slavespi.io.wbm.adr_o)
  }
}

object Spi2Wb extends App {
  println("*********")
  println("*  /!\\  *")
  println("*********")
  println("-> To Generate verilog sources choose datasize ")
  println("* For 8 bits:")
  println("$DATASIZE=8 make")
  println("* For 16 bits:")
  println("$DATASIZE=16 make")
  println("* For 16 bits with extended address:")
  println("$DATASIZE=16 EXTADDR=1 make")
  println("")
  println("No verilog generated")
}

object Spi2Wb8 extends App {
  println("****************************")
  println("* Generate 8Bits data vers *")
  println("****************************")
  println("Virgin module")
  // chisel3.Driver.execute(Array[String](), () => new Spi2Wb(8, 7))
  (new chisel3.stage.ChiselStage).execute(
      Array("-X", "verilog"),
      Seq(ChiselGeneratorAnnotation(() => new Spi2Wb(8, 7)))
  )

  println("Real world module with reset inverted")
  //chisel3.Driver.execute(Array[String](), () => new TopSpi2Wb(8))
  (new chisel3.stage.ChiselStage).execute(
      Array("-X", "verilog"),
      Seq(ChiselGeneratorAnnotation(() => new TopSpi2Wb(8)))
  )
}

object Spi2WbExt8 extends App {
  println("*****************************************************")
  println("* Generate 8Bits data with 15bits extended address *")
  println("*****************************************************")
  println("Virgin module")
  (new chisel3.stage.ChiselStage).execute(
      Array("-X", "verilog"),
      Seq(ChiselGeneratorAnnotation(() => new Spi2Wb(dwidth=8,
                                                     awidth=7,
                                                     addr_ext=true)))
  )
  println("Real world module with reset inverted")
  (new chisel3.stage.ChiselStage).execute(
      Array("-X", "verilog"),
      Seq(ChiselGeneratorAnnotation(() => new TopSpi2Wb(8, extaddr=true)))
  )
}

object Spi2Wb16 extends App {
  println("****************************")
  println("* Generate 16Bits data vers*")
  println("****************************")
  println("Virgin module")
  //chisel3.Driver.execute(Array[String](), () => new Spi2Wb(16, 7))
  (new chisel3.stage.ChiselStage).execute(
      Array("-X", "verilog"),
      Seq(ChiselGeneratorAnnotation(() => new Spi2Wb(16, 7)))
  )
  println("Real world module with reset inverted")
  //chisel3.Driver.execute(Array[String](), () => new TopSpi2Wb(16))
  (new chisel3.stage.ChiselStage).execute(
      Array("-X", "verilog"),
      Seq(ChiselGeneratorAnnotation(() => new TopSpi2Wb(16)))
  )
}


object Spi2WbExt16 extends App {
  println("*****************************************************")
  println("* Generate 16Bits data with 15bits extended address *")
  println("*****************************************************")
  println("Virgin module")
  (new chisel3.stage.ChiselStage).execute(
      Array("-X", "verilog"),
      Seq(ChiselGeneratorAnnotation(() => new Spi2Wb(dwidth=16,
                                                     awidth=15,
                                                     addr_ext=true)))
  )
  println("Real world module with reset inverted")
  (new chisel3.stage.ChiselStage).execute(
      Array("-X", "verilog"),
      Seq(ChiselGeneratorAnnotation(() => new TopSpi2Wb(dwidth=16, extaddr=true)))
  )
}

object Spi2WbExt16Burst extends App {
  println("*****************************************************")
  println("* Generate 16Bits data with 14bits extended address *")
  println("* And Burst mode activated                          *")
  println("*****************************************************")
  println("Virgin module")
  (new chisel3.stage.ChiselStage).execute(
      Array("-X", "verilog"),
      Seq(ChiselGeneratorAnnotation(() => new Spi2Wb(dwidth=16,
                                                     awidth=14,
                                                     aburst=true,
                                                     addr_ext=true)))
  )
  println("Real world module with reset inverted")
  (new chisel3.stage.ChiselStage).execute(
      Array("-X", "verilog"),
      Seq(ChiselGeneratorAnnotation(() => new TopSpi2Wb(dwidth=16,
                                                        aburst=true,
                                                        extaddr=true)))
  )
}
