/* Syntax-level stub for parsing only — not a real libc. See c_parser.py. */
#ifndef _CODECARTO_STUB_SYS_TIME_H
#define _CODECARTO_STUB_SYS_TIME_H

#include <sys/types.h>

struct timeval {
    time_t      tv_sec;
    suseconds_t tv_usec;
};

struct timezone {
    int tz_minuteswest;
    int tz_dsttime;
};

int gettimeofday(struct timeval *tv, struct timezone *tz);
int settimeofday(const struct timeval *tv, const struct timezone *tz);
int utimes(const char *filename, const struct timeval times[2]);

#endif
