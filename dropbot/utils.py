from hashlib import sha1
import zlib
import redis
import logging


class EVEAPIRedisCache(object):

    def __init__(self, redis):
        self.redis = redis

    @staticmethod
    def gen_key(host, path, params):
        params = ''.join(['{}={}'.format(x, y) for x, y in params.items()])
        key_hash = ''.join((host, path, params))
        return 'eveapi_cache_{}'.format(sha1(key_hash).hexdigest())

    def retrieve(self, host, path, params):
        key = self.gen_key(host, path, params)
        try:
            val = self.redis.get(key)
        except redis.RedisError:
            logging.exception('Error retrieving an EVE API call to Redis')
            val = None
            pass
        if val:
            return zlib.decompress(val)

    def store(self, host, path, params, doc, obj):
        key = self.gen_key(host, path, params)
        cache_time = obj.cachedUntil - obj.currentTime
        if cache_time > 0:
            val = zlib.compress(doc, 9)
            try:
                self.redis.set(key, val)
                self.redis.expire(key, cache_time)
            except redis.RedisError:
                logging.exception('Error storing an EVE API call to Redis')
                pass
