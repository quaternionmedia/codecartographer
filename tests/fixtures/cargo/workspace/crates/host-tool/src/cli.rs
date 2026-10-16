pub struct Args {
    pub data: Vec<u8>,
}

pub fn parse() -> Args {
    Args { data: std::env::args().skip(1).flat_map(String::into_bytes).collect() }
}

pub fn verbose() -> bool {
    std::env::var("VERBOSE").is_ok_and(|v| v == 1)
}
