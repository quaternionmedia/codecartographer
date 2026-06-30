/* Fallback stub — only used if libclang's own resource-dir stddef.h isn't
 * found (parse-time syntax aid; not a real libc). See c_parser.py. */
#ifndef _CODECARTO_STUB_STDDEF_H
#define _CODECARTO_STUB_STDDEF_H

#ifndef __cplusplus
typedef int wchar_t;
#endif

typedef unsigned long size_t;
typedef long          ptrdiff_t;
#define NULL ((void *)0)
#define offsetof(type, member) ((size_t)&((type *)0)->member)

#endif
