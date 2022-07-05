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

class MSNBCSpider(BaseSpider):
    """ Spider for MSNBC """
    name = 'msnbc'
    rotate_user_agent = True
    allowed_domains = ['www.msnbc.com']
    start_urls = ['https://www.msnbc.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.msnbc\.com\/\w.*\/\w.*$'),
                    deny=(
                        r'www\.msnbc\.com\/live',
                        r'www\.msnbc\.com\/schedule',
                        r'www\.msnbc\.com\/podcasts',
                        r'www\.msnbc\.com\/newsletters',
                        r'www\.msnbc\.com\/transcripts',
                        r'www\.msnbc\.com\/archive',
                        r'www\.msnbc\.com\/information\/closed-captioning',
                        r'www\.msnbc\.com\/msnbc\/msnbc-live-audio-listen-msnbc-live-stream-audio-all-day'
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

        creation_date = response.xpath('//meta[@itemprop="datePublished"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('T')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//*[@id="content"]//p[not(contains(@class,"menu-section-heading")) and not(contains(@class,"byline-bio")) and not(ancestor::div[@class="copy"])]')]
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

        item['news_outlet'] = 'msnbc'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//meta[contains(@name, "branch:deeplink:authorName")]/@content').getall()
        item['author_person'] = authors if authors else list()
        item['author_organization'] = list()
       
        # Extract keywords, if available
        item['news_keywords'] = list()

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
