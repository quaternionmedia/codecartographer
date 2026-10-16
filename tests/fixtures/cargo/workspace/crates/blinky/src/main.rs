#![no_std]
#![no_main]

use cortex_m_rt::{entry, exception};
use hal::gpio::{OutputPin, Pin};
use panic_halt as _;

static mut TICKS: u32 = 0;

#[entry]
fn main() -> ! {
    let mut led = Pin::new(5);
    loop {
        led.set_high();
        delay();
        led.set_low();
        delay();
    }
}

fn delay() {
    for _ in 0..10_000 {
        unsafe { core::arch::asm!("nop") }
    }
}

#[exception]
fn SysTick() {
    unsafe { TICKS += 1 }
}

#[no_mangle]
#[link_section = ".ram_func"]
pub extern "C" fn fast_path(x: u32) -> u32 {
    x.wrapping_mul(3)
}
