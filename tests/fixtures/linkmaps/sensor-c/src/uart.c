#include "uart.h"

#include <string.h>

#define USART2_BASE 0x40004400u
#define USART2 ((volatile uint32_t *)USART2_BASE)
#define SR 0
#define DR 1
#define BRR 2
#define CR1 3

static uint8_t rx_buffer[UART_RX_SIZE];
static volatile size_t rx_head, rx_tail;

void uart_init(uint32_t baud)
{
    USART2[BRR] = 16000000u / baud;
    USART2[CR1] = (1u << 13) | (1u << 5) | (1u << 3) | (1u << 2);
    memset(rx_buffer, 0, sizeof rx_buffer);
}

void uart_write(const uint8_t *data, size_t len)
{
    while (len--) {
        while (!(USART2[SR] & (1u << 7))) {
        }
        USART2[DR] = *data++;
    }
}

size_t uart_read(uint8_t *out, size_t max)
{
    size_t n = 0;
    while (n < max && rx_tail != rx_head) {
        out[n++] = rx_buffer[rx_tail];
        rx_tail = (rx_tail + 1) % UART_RX_SIZE;
    }
    return n;
}

void USART2_IRQHandler(void)
{
    if (USART2[SR] & (1u << 5)) {
        rx_buffer[rx_head] = (uint8_t)USART2[DR];
        rx_head = (rx_head + 1) % UART_RX_SIZE;
    }
}
