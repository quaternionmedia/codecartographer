/* Syntax-level stub for parsing only — not a real libc. See c_parser.py. */
#ifndef _CODECARTO_STUB_DIRENT_H
#define _CODECARTO_STUB_DIRENT_H

#include <sys/types.h>

typedef struct DIR DIR;

struct dirent {
    ino_t d_ino;
    char  d_name[256];
};

DIR *opendir(const char *name);
struct dirent *readdir(DIR *dirp);
int closedir(DIR *dirp);
void rewinddir(DIR *dirp);
long telldir(DIR *dirp);
void seekdir(DIR *dirp, long loc);

#endif
