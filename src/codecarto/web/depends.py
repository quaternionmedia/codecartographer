import redis

# Connect to your local Redis instance
redis_conn = redis.StrictRedis(host="localhost", port=8081, db=0)


def get_redis_conn() -> redis.StrictRedis:
    return redis_conn
