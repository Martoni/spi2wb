scalaVersion     := "2.12.12"
version          := "1.5.1"
organization     := "org.armadeus"

lazy val root = (project in file("."))
  .settings(
    name := "spi2wb",
    libraryDependencies ++= Seq(
      "edu.berkeley.cs" %% "chisel3" % "3.5.0-RC1",
      "edu.berkeley.cs" %% "chiseltest" % "0.3.2" % "test",
      "org.armadeus" %% "wbplumbing" % "0.1-SNAPSHOT"
    ),
    scalacOptions ++= Seq(
      "-Xsource:2.11",
      "-language:reflectiveCalls",
      "-deprecation",
      "-feature",
      "-Xcheckinit"
    ),
    addCompilerPlugin("edu.berkeley.cs" % "chisel3-plugin" % "3.5.0-RC1" cross CrossVersion.full),
    addCompilerPlugin("org.scalamacros" % "paradise" % "2.1.1" cross CrossVersion.full)
  )
