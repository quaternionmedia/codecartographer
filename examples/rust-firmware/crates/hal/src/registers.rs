/// The GPIO register block, laid out as the reference manual draws it.
#[repr(C)]
pub struct GpioBlock {
    pub moder: u32,
    pub otyper: u32,
    pub ospeedr: u32,
    pub pupdr: u32,
    pub idr: u32,
    pub odr: u32,
    pub bsrr: u32,
}

pub const GPIOA: *mut GpioBlock = 0x4002_0000 as *mut GpioBlock;

#[repr(u8)]
pub enum Mode {
    Input = 0,
    Output = 1,
    Alternate = 2,
    Analog = 3,
}
