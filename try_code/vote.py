'''
Redis in action
'''
import redis
import time


ONE_WEEK_IN_SECONDS = 7 * 86400
VOTE_SCORE = 432  # 一天的秒数（86400）/文章展示一天所需的支持票数（200）
ARTICLE_PER_PAGE = 25

def article_vote(conn, user, article, up=True):
    up_weight = 1 if up else -1
    cutoff = time.time() - ONE_WEEK_IN_SECONDS
    # 超过一周的数据不进行投票
    if conn.zscore('time:', article) < cutoff: return
    article_id = article.partition(':')[-1]  # 标识符写入数据库的时候为:
    # 如果投票者是第一次投这个文章
    if conn.sadd('voted:' + article_id, user):
        conn.zincrby('score:', article, up_weight*VOTE_SCORE)  # 增加投票分
        conn.hincrby(article, 'votes', up_weight*1)
    
def post_article(conn, user, title, link):
    '''发布文章
    '''
    article_id = str(conn.incr('article:'))  # 原始ID+1 -> 新ID

    voted = 'voted:' + article_id
    conn.sadd(voted, user)
    conn.expire(voted, ONE_WEEK_IN_SECONDS)  # 过期时间设置为一周

    now = time.time()
    article = 'article:' + article_id
    # 将文章信息存储在一个散列里面
    conn.hmset(article, {
        'title': title,
        'link': link,
        'poster': user,
        'time': now,
        'votes': 1,
    })
    conn.zadd('score:', article, now+VOTE_SCORE)
    conn.zadd('time:', article, now)

    return article_id

def get_articles(conn, page, order='score:'):
    '''获取分数最高的文章
    '''
    start = (page - 1) * ARTICLE_PER_PAGE
    end = start + ARTICLE_PER_PAGE - 1

    ids = conn.zrevrange(order, start, end)
    aritcles = []
    for id in ids:
        article_data = conn.hgetall(id)
        article_data['id'] = id
        aritcles.append(article_data)
    
    return aritcles

def get_group_articles(conn, group, page, order='score:'):
    key = order + group
    # 检查是否有已缓存的排序结果
    if not conn.exists(key):
        conn.zinterstore(key, 
            ['group:' + group, order],
            aggregate='max',
        )
        conn.expire(key, 60)  # 60s后自动删除这个有序集合
    return get_articles(conn, page, key)

def add_remove_groups(conn, article_id, to_add=[], to_remove=[]):
    '''将文章添加到群组
    '''
    article = 'article:' + article_id
    # 将文章添加到所属的群组里
    for group in to_add: conn.sadd('group:' + group, article)
    for group in to_remove: conn.srem('group:' + group, article)




def main():
    conn = redis.Redis()  # 创建一个指向Redis的连接