package spi2wb

import chisel3._
import circt.stage.ChiselStage
import chisel3.util._

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

  val spiAddressWidth  = (addr_ext, aburst) match {
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

  val wrReg  = RegInit(false.B)  // Read flag
  val wbFlag = RegInit(false.B)  // burst flag

  val count = RegInit(0.U(dwidth.W))
  //   000    001     010     011        100     101         110     111
  val sinit::swrreg::swbreg::saddr::sdataread::swbread::sdatawrite::swbwrite::Nil=Enum(8)
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
        if(aburst)
          stateReg := swbreg
        else
          stateReg := saddr
      }
    }
    is(swbreg){
      when(fallingedge(sclkReg)){
        wbFlag := io.spi.mosi
        stateReg := saddr
      }
    }
    is(saddr){
      when(fallingedge(sclkReg)){
        addrReg := addrReg(awidth - 1, 0) ## io.spi.mosi
        count := count + 1.U
        when(count >= spiAddressWidth.U) {
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
        if(!aburst)
          wbCycReg := false.B
        dataReg  := io.wbm.dat_i
        stateReg := sdataread
      }
    }
    is(sdataread){
      when(risingedge(sclkReg)){
        misoReg := dataReg(((spiAddressWidth + dwidth).U - count)(log2Ceil(dwidth)-1, 0))
        count := count + 1.U
      }
      if (!aburst)
      when(count >= (2 + spiAddressWidth + dwidth).U){
          stateReg := sinit
      }
      else{
        when(count >= (1 + spiAddressWidth + dwidth).U){
          when(fallingedge(sclkReg)){
            addrReg := addrReg + 1.U
            count := (spiAddressWidth + 1).U
            wbWeReg  := false.B
            wbStbReg := true.B
            stateReg := swbread
          }
        }
      }
    }
    is(sdatawrite){
      when(fallingedge(sclkReg)){
        dataReg := dataReg(dwidth-2, 0) ## io.spi.mosi
        count := count + 1.U
      }
      when(count >= (1 + spiAddressWidth + dwidth).U){
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
          if(!aburst){
            wbCycReg := false.B
            stateReg := sinit
          }else{
            addrReg := addrReg + 1.U
            count := (spiAddressWidth + 1).U
            dataReg := 0.U
            stateReg := sdatawrite
          }
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

object Spi2Wb8 extends App {
  println("****************************")
  println("* Generate 8Bits data vers *")
  println("****************************")

  ChiselStage.emitSystemVerilogFile(
    new Spi2Wb(dwidth=8, awidth=7),
    firtoolOpts = Array(
      "-disable-all-randomization",
      "--lowering-options=disallowLocalVariables", // avoid 'automatic logic'
      "-strip-debug-info"),
    args=args)
}

object Spi2WbExt8 extends App {
  println("*****************************************************")
  println("* Generate 8Bits data with 15bits extended address *")
  println("*****************************************************")

  ChiselStage.emitSystemVerilogFile(
    new Spi2Wb(dwidth=8, awidth=7, addr_ext=true),
    firtoolOpts = Array(
      "-disable-all-randomization",
      "--lowering-options=disallowLocalVariables", // avoid 'automatic logic'
      "-strip-debug-info"),
    args=args)
}

object Spi2Wb16 extends App {
  println("****************************")
  println("* Generate 16Bits data vers*")
  println("****************************")

  ChiselStage.emitSystemVerilogFile(
    new Spi2Wb(dwidth=16, awidth=7),
    firtoolOpts = Array(
      "-disable-all-randomization",
      "--lowering-options=disallowLocalVariables", // avoid 'automatic logic'
      "-strip-debug-info"),
    args=args)
}


object Spi2WbExt16 extends App {
  println("*****************************************************")
  println("* Generate 16Bits data with 15bits extended address *")
  println("*****************************************************")

  ChiselStage.emitSystemVerilogFile(
    new Spi2Wb(dwidth=16, awidth=15, addr_ext=true),
    firtoolOpts = Array(
      "-disable-all-randomization",
      "--lowering-options=disallowLocalVariables", // avoid 'automatic logic'
      "-strip-debug-info"),
    args=args)
}

object Spi2WbExt16Burst extends App {
  println("*****************************************************")
  println("* Generate 16Bits data with 14bits extended address *")
  println("* And Burst mode activated                          *")
  println("*****************************************************")

  ChiselStage.emitSystemVerilogFile(
    new Spi2Wb(dwidth=16, awidth=14, aburst=true, addr_ext=true),
    firtoolOpts = Array(
      "-disable-all-randomization",
      "--lowering-options=disallowLocalVariables", // avoid 'automatic logic'
      "-strip-debug-info"),
    args=args)
}
