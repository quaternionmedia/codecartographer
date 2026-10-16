use heapless::Vec;

pub enum Event {
    Received(u8),
    Overrun,
    Frame { byte: u8, at: u32 },
}

pub struct Uart {
    buffer: Vec<u8, 64>,
    errors: u32,
}

impl Uart {
    pub fn poll(&mut self) -> Option<Event> {
        self.drain();
        None
    }

    fn drain(&mut self) {
        self.buffer.clear();
    }
}
