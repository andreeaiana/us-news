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

class RealClearPoliticsSpider(BaseSpider):
    """ Spider for RealClearPolitics """
    name = 'real_clear_politics'
    rotate_user_agent = True
    allowed_domains = ['www.realclearpolitics.com']
    start_urls = ['https://www.realclearpolitics.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.realclearpolitics\.com\/\w.*\.html$'),
                    deny=(
                        r'www\.realclearpolitics\.com\/video\/',
                        r'www\.realclearpolitics\.com\/authors\/',
                        r'www\.realclearpolitics\.com\/daily\_newsletters\/',
                        r'www\.realclearpolitics\.com\/podcasts\/',
                        r'www\.realclearpolitics\.com\/cartoons\/',
                        r'www\.realclearpolitics\.com\/links\/',
                        r'www\.realclearpolitics\.com\/realclearpublishing\/',
                        r'www\.realclearpolitics\.com\/rss\/',
                        r'www\.realclearpolitics\.com\/speakers\.html',
                        r'www\.realclearpolitics\.com\/about\.html',
                        r'www\.realclearpolitics\.com\/privacy\.html',
                        r'www\.realclearpolitics\.com\/contact\.html',
                        r'www\.realclearpolitics\.com\/media_kit\/contact\_us\.html'
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

        creation_date = response.xpath('//span[@class="auth-date"]/text()').get()
        if not creation_date:
            return
        creation_date = datetime.strptime(creation_date, '%B %d, %Y')
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(ancestor::div[@id="author-bio"]) and not(preceding-sibling::p[@id="author-bio"])] | //ul/li[not(descendant::a)]')]
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

        item['news_outlet'] = 'real_clear_politics'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//div[@class="auth-author"]/a/text() | //div[@class="auth-byline"]/a/text()').getall()
        item['author_person'] = authors if authors else list()
        item['author_organization'] = list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//meta[@name="keywords"]/@content').get()
        item['news_keywords'] = news_keywords.split(',') if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@name="description"]/@content').get().strip()

         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        # The article has no headlines, just paragraphs
        body[''] = paragraphs

        item['content'] = {'title': title, 'description': description, 'body':body}

        # There are no recommendations to other related articles
        item['recommendations'] = list()

        item['response_body'] = response.body
        
        yield item
