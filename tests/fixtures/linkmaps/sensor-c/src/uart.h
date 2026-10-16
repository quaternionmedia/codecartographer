#ifndef UART_H
#define UART_H

#include <stddef.h>
#include <stdint.h>

#define UART_RX_SIZE 256

void uart_init(uint32_t baud);
void uart_write(const uint8_t *data, size_t len);
size_t uart_read(uint8_t *out, size_t max);

#endif
