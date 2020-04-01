import time
import redis


QUIT = False
LIMIT = 100000000


def check_token(conn, token):
    return conn.hget('login:', token)

def update_token(conn, token, user, item=None):
    '''更新令牌
    将用户的令牌和当前时间戳添加到记录最近登录用户的有序集合里;
    将商品添加到记录这个用户最近浏览过的商品的有序集合里面，并在被记录商品的
    数量超过25个时，对有序集合进行修剪.
    '''
    timestamp = time.time()
    # 维持令牌与已登录用户之间的映射
    conn.hset('login:', token, user)
    # 记录令牌最后一次出现的时间
    conn.zadd('recent:', token, timestamp)
    if item:  # 记录用户浏览过的商品
        conn.zadd('viewed:' + token, item, timestamp)
        conn.zremrangebyrank('viewed:' + token, 0, -26)

def clean_sessions(conn):
    while not QUIT:
        size = conn.zcard('recent:')
        if size <= LIMIT:
            time.sleep(1)
            continue
        end_index = min(size - LIMIT, 100)  # 最多删除100条
        tokens = conn.zrange('recent:', 0, end_index-1)

        session_keys = []
        for token in tokens:
            session_keys.append('viewed:' + token)
            session_keys.append('cart:' + token)
        conn.delete(*session_keys)
        conn.hdel('login:', *tokens)
        conn.zrem('recent:', *tokens)

def add_to_cart(conn, session, item, count):
    '''添加购物车
    '''
    if count <= 0:
        conn.hrem('cart:' + session, item)
    else:
        conn.hset('cart:' + session, item, count)

def cache_request(conn, request, callback):
    if not can_cache(conn, request): return callback(request)
    page_key = 'cache:' + hash_request(request)
    content = conn.get(page_key)

    if not content:
        content = callback(request)
        conn.setex(page_key, content, 300)  # 5min
    
    return content
