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

class CommonDreamsSpider(BaseSpider):
    """ Spider for Common Dreams News Center """
    name = 'common_dreams'
    rotate_user_agent = True
    allowed_domains = ['www.commondreams.org']
    start_urls = ['https://www.commondreams.org']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.commondreams\.org\/\w.*\/\d+\/\d+\/\d+\/\w.*$'),
                    deny=(
                        r'www\.commondreams\.org\/about-us',
                        r'www\.commondreams\.org\/key-staff',
                        r'www\.commondreams\.org\/contact-us',
                        r'www\.commondreams\.org\/what-they-are-saying',
                        r'www\.commondreams\.org\/privacy-policy',
                        r'www\.commondreams\.org\/ethics-policy',
                        r'www\.commondreams\.org\/corrections-updates',
                        r'www\.commondreams\.org\/fact-checking-policy',
                        r'www\.commondreams\.org\/republishing-our-work',
                        r'www\.commondreams\.org\/ownership-funding',
                        r'www\.commondreams\.org\/submission-guidelines'
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

        creation_date = response.xpath('//meta[@property="article:modified_time"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('T')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[contains(@class, "node__body") or contains(@class, "newswire__body")]/p[not(@class="pullquote")] | //blockquote/p | //ul/li/p')]
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

        item['news_outlet'] = 'common_dreams'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@property="article:modified_time"]/@content').get()
        last_modified = datetime.fromisoformat(last_modified.split('T')[0])
        item['last_modified'] = last_modified.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//span[@typeof="schema:Person" and @property="schema:name"]/a/text()').getall()
        item['author_person'] = [author for author in authors if author != 'Common Dreams staff'] if authors else list()
        item['author_organization'] = ['Common Dreams staff'] if authors and 'Common Dreams staff' in authors else list()
       
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
