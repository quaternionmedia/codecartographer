/* Fallback stub — only used if libclang's own resource-dir stddef.h isn't
 * found (parse-time syntax aid; not a real libc). See c_parser.py. */
#ifndef _CODECARTO_STUB_STDDEF_H
#define _CODECARTO_STUB_STDDEF_H

/* The target's own widths: clang predefines __SIZE_TYPE__ and its kin for
 * every target, so a Linux, a Windows and a Cortex-M parse each get the type
 * that target has -- and agree with a header, or the compiler's own implicit
 * declaration on an MSVC target, that declares it too. A fixed
 * `unsigned long` was a redefinition on Windows, where size_t is 64 bits in a
 * 32-bit long. */
#ifndef __cplusplus
typedef __WCHAR_TYPE__ wchar_t;
#endif

typedef __SIZE_TYPE__    size_t;
typedef __PTRDIFF_TYPE__ ptrdiff_t;
#define NULL ((void *)0)
#define offsetof(type, member) ((size_t)&((type *)0)->member)

#endif
