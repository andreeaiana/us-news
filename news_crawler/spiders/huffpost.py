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

class HuffpostSpider(BaseSpider):
    """ Spider for Huffpost """
    name = 'huffpost'
    rotate_user_agent = True
    allowed_domains = ['www.huffpost.com']
    start_urls = ['https://www.huffpost.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.huffpost\.com\/entry\/\w.*$'),
                    deny=(
                        r'www\.huffpost\.com\/section\/video',
                        r'www\.huffpost\.com\/horoscopes',
                        r'www\.huffpost\.com\/newsletters',
                        r'www\.huffpost\.com\/syndication',
                        r'www\.huffpost\.com\/life\/huffpost-shopping',
                        r'www\.huffpost\.com\/static\/\w.*'
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

        creation_date = response.xpath('//time/@datetime').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('T')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="primary-cli cli cli-text "]')]
        paragraphs = remove_empty_paragraphs(paragraphs)
        paragraphs = paragraphs[:-1] # Remove advertisement in last line
        text = ' '.join([para for para in paragraphs])

        # Check article's length validity
        if not self.has_min_length(text):
            return

        # Check keywords validity
        if not self.has_valid_keywords(text):
            return

        # Parse the valid article
        item = NewsCrawlerItem()

        item['news_outlet'] = 'huffpost'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//div[@class="entry__byline__author"]/a/@data-vars-item-name | //div[@class="entry__wirepartner entry-wirepartner"]/span/text()').getall()        
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

        # Top 5 recommendations to other related news articles from the same outlet
        recommendations = response.xpath('//div[@class="cli-related-articles__content-wrapper"]/div/a/@href').getall()
        if recommendations:
            item['recommendations'] = list(set(recommendations))[:5]
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body
        
        yield item
