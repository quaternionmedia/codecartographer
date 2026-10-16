#include <stdint.h>
#include <string.h>

#include "crc.h"
#include "uart.h"

struct config {
    uint32_t baud;
    uint32_t period_ms;
    uint8_t node_id;
};

struct config config = {115200, 250, 7};
static const char banner[] = "sensor-c ready\r\n";
static volatile uint32_t ticks;

void SysTick_Handler(void)
{
    ticks++;
}

static void delay_ms(uint32_t ms)
{
    uint32_t start = ticks;
    while (ticks - start < ms) {
    }
}

int main(void)
{
    uint8_t frame[32];
    uart_init(config.baud);
    uart_write((const uint8_t *)banner, sizeof banner - 1);
    for (;;) {
        size_t n = uart_read(frame, sizeof frame - 4);
        if (n) {
            uint32_t crc = crc32_update(0, frame, n);
            memcpy(frame + n, &crc, sizeof crc);
            uart_write(frame, n + sizeof crc);
        }
        delay_ms(config.period_ms);
    }
}
