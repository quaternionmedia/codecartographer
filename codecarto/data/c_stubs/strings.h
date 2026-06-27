/* Syntax-level stub for parsing only — not a real libc. See c_parser.py. */
#ifndef _CODECARTO_STUB_STRINGS_H
#define _CODECARTO_STUB_STRINGS_H

#include <sys/types.h>

int strcasecmp(const char *a, const char *b);
int strncasecmp(const char *a, const char *b, size_t n);
int bcmp(const void *a, const void *b, size_t n);
void bcopy(const void *src, void *dst, size_t n);
void bzero(void *s, size_t n);
int ffs(int i);

#endif
