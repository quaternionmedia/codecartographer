/* Syntax-level stub for parsing only — not a real libc. See c_parser.py.
 * Pulls in the type definitions most POSIX code expects transitively from
 * <unistd.h>, so downstream "unknown type name" cascades (uint32_t, ssize_t,
 * pid_t, ...) resolve even when the real system header isn't available. */
#ifndef _CODECARTO_STUB_UNISTD_H
#define _CODECARTO_STUB_UNISTD_H

#include <stdint.h>
#include <sys/types.h>

#define STDIN_FILENO  0
#define STDOUT_FILENO 1
#define STDERR_FILENO 2

#define SEEK_SET 0
#define SEEK_CUR 1
#define SEEK_END 2

#define F_OK 0
#define R_OK 4
#define W_OK 2
#define X_OK 1

ssize_t read(int fd, void *buf, size_t count);
ssize_t write(int fd, const void *buf, size_t count);
int     close(int fd);
off_t   lseek(int fd, off_t offset, int whence);
int     access(const char *path, int mode);
int     unlink(const char *path);
int     rmdir(const char *path);
int     chdir(const char *path);
char   *getcwd(char *buf, size_t size);
pid_t   fork(void);
pid_t   getpid(void);
pid_t   getppid(void);
int     execv(const char *path, char *const argv[]);
int     execvp(const char *file, char *const argv[]);
unsigned int sleep(unsigned int seconds);
int     usleep(unsigned int usec);
int     pipe(int fd[2]);
int     dup(int fd);
int     dup2(int oldfd, int newfd);
long    sysconf(int name);
int     isatty(int fd);

#endif
