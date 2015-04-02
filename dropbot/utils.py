from hashlib import sha1
import zlib
import redis
import logging
import math


def decimal_minutes_to_hms(minutes):
    """Converts a value of decimal minutes into a hms format"""
    if not isinstance(minutes, (int, float, long)):
        if isinstance(minutes, basestring):
            try:
                minutes = float(minutes)
            except ValueError:
                raise ValueError('minutes is not a valid number')
        else:
            raise ValueError('minutes is not a valid number')

    # If we have a negative number, invert
    if minutes < 0:
        minutes = -1 * minutes

    out_secs = round(60 * (minutes % 1))
    out_minutes = math.floor(minutes) % 60
    out_hours = math.floor(math.floor(minutes) / 60)

    output = ''
    if out_hours > 0:
        output += '{}h '.format(int(out_hours))
    if out_minutes > 0:
        output += '{}m '.format(int(out_minutes))
    if out_secs > 0:
        output += '{}s '.format(int(out_secs))
    return output.strip()


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
