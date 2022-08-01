# -*- coding: utf-8 -*-

import os
import sys
from news_crawler.spiders import BaseSpider
from scrapy.spiders import Rule 
from scrapy.linkextractors import LinkExtractor
from datetime import datetime

sys.path.insert(0, os.path.join(os.getcwd(), "..",))
from news_crawler.items import NewsCrawlerItem
from news_crawler.utils import remove_empty_paragraphs

class RealNewsNetworkSpider(BaseSpider):
    """ Spider for The Real News Network (TRNN) """
    name = 'real_news_network'
    rotate_user_agent = True
    allowed_domains = ['therealnews.com']
    start_urls = ['https://therealnews.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'therealnews\.com\/\w.*$'),
                    deny=(
                        r'therealnews\.com\/about',
                        r'therealnews\.com\/about\/our-team',
                        r'therealnews\.com\/join-us',
                        r'therealnews\.com\/more-ways-to-give',
                        r'therealnews\.com\/store'
                        )
                    ),
                callback='parse_item',
                follow=True
                ),
            )

    def parse_item(self, response):
        """
        Checks article validity. If valid, it parses it.
        """

        creation_date = response.xpath('//time[@class="entry-date published"]/@datetime').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('T')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="entry-content"]/p[not(@*)] | //div[@class="entry-content"]/p[@class="has-drop-cap"] | //div[@class="entry-content"]/blockquote/p')]
        paragraphs = remove_empty_paragraphs(paragraphs)
        text = ' '.join([para for para in paragraphs])

        # Check article's length validity
        if not self.has_min_length(text):
            return

        # Check keywords validity
        if not self.has_valid_keywords(text):
            return

        # Parse the valid article
        item = NewsCrawlerItem()

        item['news_outlet'] = 'real_news_network'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//time[@class="updated"]/@datetime').get()
        last_modified = datetime.fromisoformat(last_modified.split('T')[0])
        item['last_modified'] = last_modified.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//span[@class="author vcard"]/a/text()').getall()
        item['author_person'] = authors if authors else list()
        item['author_organization'] = list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//span[@class="tags-links"]/a[@rel="tag"]/text()').getall()
        item['news_keywords'] = news_keywords if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@name="description"]/@content').get().strip()

         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        # The article has no headlines, just paragraphs
        body[''] = paragraphs

        item['content'] = {'title': title, 'description': description, 'body':body}

        # There are no recommendations to other related articles
        recommendations = response.xpath('//nav[@class="jp-relatedposts-i2"]/div/ul/li/a/@href').getall()
        item['recommendations'] = list(set(recommendations))[:5] if recommendations else list()

        item['response_body'] = response.body
        
        yield item
