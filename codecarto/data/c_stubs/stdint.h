/* Fallback stub — only used if libclang's own resource-dir stdint.h isn't
 * found (parse-time syntax aid; not a real libc). See c_parser.py. */
#ifndef _CODECARTO_STUB_STDINT_H
#define _CODECARTO_STUB_STDINT_H

typedef signed char        int8_t;
typedef unsigned char       uint8_t;
typedef short               int16_t;
typedef unsigned short      uint16_t;
typedef int                 int32_t;
typedef unsigned int        uint32_t;
typedef long long           int64_t;
typedef unsigned long long  uint64_t;

typedef long long           intptr_t;
typedef unsigned long long  uintptr_t;
typedef long long           intmax_t;
typedef unsigned long long  uintmax_t;

typedef int8_t   int_least8_t;
typedef uint8_t  uint_least8_t;
typedef int16_t  int_least16_t;
typedef uint16_t uint_least16_t;
typedef int32_t  int_least32_t;
typedef uint32_t uint_least32_t;
typedef int64_t  int_least64_t;
typedef uint64_t uint_least64_t;

#endif
