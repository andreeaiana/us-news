# -*- coding: utf-8 -*-

import os
import sys
import json
from news_crawler.spiders import BaseSpider
from scrapy.spiders import Rule 
from scrapy.linkextractors import LinkExtractor
from datetime import datetime

sys.path.insert(0, os.path.join(os.getcwd(), "..",))
from news_crawler.items import NewsCrawlerItem
from news_crawler.utils import remove_empty_paragraphs

class HannitySpider(BaseSpider):
    """ Spider for Sean Hannity """
    name = 'hannity'
    rotate_user_agent = True
    allowed_domains = ['hannity.com']
    start_urls = ['https://hannity.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'hannity\.com\/\w.*\/\w.*$'),
                    deny=(
                        r'hannity\.com\/book-sean',
                        r'hannity\.com\/find-a-station\/',
                        r'hannity\.com\/contest-guidelines\/',
                        r'hannity\.com\/terms-of-use\/',
                        r'hannity\.com\/privacy-notice\/',
                        r'hannity\.com\/podcasts\/',
                        r'hannity\.com\/contact\/'
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

        data_json = response.xpath('//script[@type="application/ld+json"]/text()').get()
        if not data_json:
            return
        
        data = json.loads(data_json)
        creation_date = data['datePublished']
        if not creation_date:
            return
        creation_date = datetime.strptime(creation_date, '%B %d, %Y')
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p')]
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

        item['news_outlet'] = 'hannity'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = data['dateModified']
        last_modified = datetime.strptime(last_modified, '%B %d, %Y')
        item['last_modified'] = last_modified.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = data['author']['name'] 
        item['author_person'] = [authors] if authors and authors != 'Hannity Staff' else list()
        item['author_organization'] = [authors] if authors and authors == 'Hannity Staff' else list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//meta[@name="keywords"]/@content').get()
        item['news_keywords'] = news_keywords.split(', ') if news_keywords else list()

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
