mod pin;

pub use pin::Pin;

/// A pin that can be driven.
pub trait OutputPin {
    fn set_high(&mut self);
    fn set_low(&mut self);
}
