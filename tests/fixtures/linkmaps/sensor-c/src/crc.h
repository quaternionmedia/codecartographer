#ifndef CRC_H
#define CRC_H

#include <stddef.h>
#include <stdint.h>

extern uint32_t crc_calls;
uint32_t crc32_update(uint32_t crc, const uint8_t *data, size_t len);

#endif
