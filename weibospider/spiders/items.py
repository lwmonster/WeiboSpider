import scrapy


class WeiboItem(scrapy.Item):
    id = scrapy.Field()
    user = scrapy.Field()
    content = scrapy.Field()
    comments = scrapy.Field(default=[])
