val majorChiselVersion = "6"
val minorChiselVersion = "2"
val chiselVersion = majorChiselVersion + "." + minorChiselVersion + ".0"

scalaVersion     := "2.13.12"
version          := majorChiselVersion + "." + minorChiselVersion + ".0"
organization     := "org.armadeus"

credentials += Credentials(
  "GitHub Package Registry",
  "maven.pkg.github.com",
  "_",
  System.getenv("GITHUB_TOKEN")
)

resolvers ++= Seq("GitHub WbPlumbing Martoni Apache Maven Packages" at "https://maven.pkg.github.com/Martoni/WbPlumbing")

lazy val root = (project in file("."))
  .settings(
    name := "spi2wb",
    libraryDependencies ++= Seq(
      "org.chipsalliance" %% "chisel" % chiselVersion,
      "org.scalatest" %% "scalatest" % "3.2.19" % "test",
      "org.armadeus" %% "wbplumbing" % "6.2.6"
    ),
    scalacOptions ++= Seq(
      "-language:reflectiveCalls",
      "-deprecation",
      "-feature",
      "-Xcheckinit"
    ),
    addCompilerPlugin("org.chipsalliance" % "chisel-plugin" % chiselVersion cross CrossVersion.full),
  )

publishTo := Some("GitHub wbGPIO Martoni Apache Maven Packages" at "https://maven.pkg.github.com/Martoni/spi2wb")
publishMavenStyle := true
