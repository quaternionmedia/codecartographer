fn main() {
    cc::Build::new().file("csrc/crc.c").compile("crc");
}
