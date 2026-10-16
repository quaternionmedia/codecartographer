use super::OutputPin;
use crate::registers::{GpioBlock, GPIOA};

pub struct Pin {
    n: u8,
    block: *mut GpioBlock,
}

impl Pin {
    pub const fn new(n: u8) -> Self {
        Self { n, block: GPIOA }
    }

    fn mask(&self) -> u32 {
        1 << self.n
    }
}

impl OutputPin for Pin {
    fn set_high(&mut self) {
        let mask = self.mask();
        unsafe { core::ptr::write_volatile(&mut (*self.block).bsrr, mask) }
    }

    fn set_low(&mut self) {
        let mask = self.mask() << 16;
        unsafe { core::ptr::write_volatile(&mut (*self.block).bsrr, mask) }
    }
}
