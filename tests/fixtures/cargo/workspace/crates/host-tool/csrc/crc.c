#include "crc.h"

static volatile uint32_t calls;

struct crc_state {
    uint32_t value;
    size_t length;
};

uint32_t crc32(const uint8_t *data, size_t len) {
    struct crc_state state = {0xFFFFFFFFu, len};
    calls++;
    for (size_t i = 0; i < len; i++) {
        state.value ^= data[i];
        for (int bit = 0; bit < 8; bit++) {
            state.value = (state.value >> 1) ^ (0xEDB88320u & -(state.value & 1u));
        }
    }
    return ~state.value;
}
