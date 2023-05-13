#!/usr/bin/env python
# encoding: utf-8
"""
Author: liangwei
Mail: lwmonster@gmail.com
Created Time: 2023/5/09
"""
import json
import logging
from scrapy import Spider
from scrapy.http import Request
from .common import parse_tweet_info, parse_long_tweet, parse_time, url_to_mid
#from weibospider.spiders.common import parse_tweet_info, parse_long_tweet
#from spiders.common import parse_tweet_info, parse_long_tweet


class TweetAndCommentSpider(Spider):
    """
    用户推文数据采集
    """
    name = "tweet_spider"
    base_url = "https://weibo.com"
    comment_url_pattern = f"https://weibo.com/ajax/statuses/buildComments?" \
          f"is_reload=1&id=%d&is_show_bulletin=2&is_mix=0&count=20"

    def start_requests(self):
        """
        爬虫入口
        """
        # 这里user_ids可替换成实际待采集的数据
        #user_ids = ['1497035431']
        user_ids = ['7825695898']
        # with open('uids.txt', 'r') as f:
        #     for line in f:
        #         line = line.strip()
        #         cols = line.split()
        #         user_ids.append(cols[0])

        for user_id in user_ids:
            url = f"https://weibo.com/ajax/statuses/mymblog?uid={user_id}&page=1"
            logging.info('processing %s ......' % user_id)
            yield Request(url, callback=self.parse, meta={'user_id': user_id, 'page_num': 1})

    def parse(self, response, **kwargs):
        """
        网页解析
        """
        data = json.loads(response.text)
        tweets = data['data']['list']
        logging.info('got tweets:%s' % str(tweets))
        for tweet in tweets:
            item = parse_tweet_info(tweet)
            del item['user']
            if item['isLongText']:
                url = "https://weibo.com/ajax/statuses/longtext?id=" + item['mblogid']
                yield Request(url, callback=parse_long_tweet, meta={'item': item})
            else:
                #yield item
                # 获取评论
                mid = url_to_mid(item['mblogid'])
                #url = f"https://weibo.com/ajax/statuses/buildComments?" \
                #      f"is_reload=1&id={mid}&is_show_bulletin=2&is_mix=0&count=20"
                url = self.comment_url_pattern % mid
                logging.info('get comment for:%s' % str(mid))
                yield Request(url, callback=self.parse_comment, meta={'item': item, 'comment_url': url})

        if tweets:
            user_id, page_num = response.meta['user_id'], response.meta['page_num']
            page_num += 1
            url = f"https://weibo.com/ajax/statuses/mymblog?uid={user_id}&page={page_num}"
            yield Request(url, callback=self.parse, meta={'user_id': user_id, 'page_num': page_num})

    def parse_long_tweet(self, response, **kwargs):
        """
        解析长推文
        """
        data = json.loads(response.text)['data']
        item = response.meta['item']
        item['content'] = data['longTextContent']
        #yield item
        mid = url_to_mid(item['mblogid'])
        url = self.comment_url_pattern % mid
        yield Request(url, callback=self.parse_comment, meta={'item': item, 'comment_url': url})

    # 解析评论
    def parse_comment(self, response, **kwargs):
        """
        解析评论
        """
        one_tweet = response.meta['item']
        data = json.loads(response.text)
        # 解析评论并添加到tweet中
        for comment_info in data['data']:
            one_comment = self.parse_comment_info(comment_info)
            one_tweet['comments'].append(one_comment)

        logging.info('got one tweet:%s' % str(one_tweet))

        # 还有评论，继续翻页获取
        if data.get('max_id', 0) != 0:
            url = response.meta['comment_url'] + '&max_id=' + str(data['max_id'])
            yield Request(url, callback=self.parse_comment,
                          meta={'item': one_tweet, 'comment_url': response.meta['comment_url']})
        else:
            logging.info('got one tweet:%s' % str(one_tweet))
            yield one_tweet

    @staticmethod
    def parse_comment_info(data):
        """
        解析comment
        """
        item = dict()
        item['created_at'] = parse_time(data['created_at'])
        item['_id'] = data['id']
        item['like_counts'] = data['like_counts']
        item['ip_location'] = data.get('source', '')
        item['content'] = data['text_raw']
        #item['comment_user'] = parse_user_info(data['user'])
        return item
