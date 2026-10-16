#include "crc.h"

static uint32_t table[256];
uint32_t crc_calls;

static void crc32_build_table(void)
{
    for (uint32_t i = 0; i < 256; i++) {
        uint32_t c = i;
        for (int k = 0; k < 8; k++)
            c = (c & 1) ? 0xEDB88320u ^ (c >> 1) : c >> 1;
        table[i] = c;
    }
}

uint32_t crc32_update(uint32_t crc, const uint8_t *data, size_t len)
{
    if (table[1] == 0)
        crc32_build_table();
    crc_calls++;
    crc = ~crc;
    while (len--)
        crc = table[(crc ^ *data++) & 0xFF] ^ (crc >> 8);
    return ~crc;
}
