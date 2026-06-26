/* Syntax-level stub for parsing only — not a real libc. See c_parser.py. */
#ifndef _CODECARTO_STUB_PTHREAD_H
#define _CODECARTO_STUB_PTHREAD_H

typedef unsigned long pthread_t;
typedef struct { int __opaque[8]; } pthread_mutex_t;
typedef struct { int __opaque[8]; } pthread_cond_t;
typedef struct { int __opaque[4]; } pthread_attr_t;
typedef struct { int __opaque[4]; } pthread_mutexattr_t;
typedef struct { int __opaque[4]; } pthread_condattr_t;
typedef unsigned long pthread_key_t;
typedef struct { int __opaque[8]; } pthread_once_t;
typedef struct { int __opaque[8]; } pthread_rwlock_t;

#define PTHREAD_MUTEX_INITIALIZER  {{0}}
#define PTHREAD_COND_INITIALIZER   {{0}}
#define PTHREAD_ONCE_INIT          {{0}}

int pthread_create(pthread_t *thread, const pthread_attr_t *attr,
                    void *(*start_routine)(void *), void *arg);
int pthread_join(pthread_t thread, void **retval);
int pthread_detach(pthread_t thread);
pthread_t pthread_self(void);
int pthread_equal(pthread_t a, pthread_t b);
void pthread_exit(void *retval);

int pthread_mutex_init(pthread_mutex_t *mutex, const pthread_mutexattr_t *attr);
int pthread_mutex_destroy(pthread_mutex_t *mutex);
int pthread_mutex_lock(pthread_mutex_t *mutex);
int pthread_mutex_trylock(pthread_mutex_t *mutex);
int pthread_mutex_unlock(pthread_mutex_t *mutex);

int pthread_cond_init(pthread_cond_t *cond, const pthread_condattr_t *attr);
int pthread_cond_destroy(pthread_cond_t *cond);
int pthread_cond_wait(pthread_cond_t *cond, pthread_mutex_t *mutex);
int pthread_cond_signal(pthread_cond_t *cond);
int pthread_cond_broadcast(pthread_cond_t *cond);

int pthread_once(pthread_once_t *once_control, void (*init_routine)(void));
int pthread_key_create(pthread_key_t *key, void (*destructor)(void *));
int pthread_setspecific(pthread_key_t key, const void *value);
void *pthread_getspecific(pthread_key_t key);

#endif
