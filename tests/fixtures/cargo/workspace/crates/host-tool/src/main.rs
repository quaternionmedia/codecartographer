mod cli;

extern "C" {
    fn crc32(data: *const u8, len: usize) -> u32;
}

fn main() {
    let args = cli::parse();
    let sum = unsafe { crc32(args.data.as_ptr(), args.data.len()) };
    println!("{sum:08x}");
}
