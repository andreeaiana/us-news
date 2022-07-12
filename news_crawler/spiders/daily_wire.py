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

class DailyWireSpider(BaseSpider):
    """ Spider for The Daily Wire """
    name = 'daily_wire'
    rotate_user_agent = True
    allowed_domains = ['www.dailywire.com']
    start_urls = ['https://www.dailywire.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.dailywire\.com\/news\/\w.*$'),
                    deny=(
                        r'www\.dailywire\.com\/about',
                        r'www\.dailywire\.com\/authors',
                        r'www\.dailywire\.com\/speakers',
                        r'www\.dailywire\.com\/terms',
                        r'www\.dailywire\.com\/privacy',
                        r'www\.dailywire\.com\/listen'
                        r'www\.dailywire\.com\/watch',
                        r'www\.dailywire\.com\/discuss',
                        r'www\.dailywire\.com\/shop',
                        r'www\.dailywire\.com\/standards-policies',
                        r'www\.dailywire\.com\/shipping-returns-policy'
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

        # Ignore articles for members only
        data_json = response.xpath('//script[@type="application/json"]/text()').get()
        if data_json:
            data = json.loads(data_json)
            if data['props']['pageProps']['post']['members_only']==True:
                return

        creation_date = response.xpath('//meta[@name="parsely-pub-date"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('T')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@id="post-body-text"]//p')]
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

        item['news_outlet'] = 'daily_wire'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//span/a/strong[@class="css-1srl04s"]/text()').getall()
        item['author_person'] = authors if authors else list()
        item['author_organization'] = list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//meta[@name="parsely-tags"]/@content').get()
        item['news_keywords'] = news_keywords.split(',') if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        desc_json = response.xpath('//script[@type="application/ld+json"]/text()').get()
        if desc_json:
            desc_data = json.loads(desc_json)
            description = desc_data['description']
        else:
            description = ''

         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        # The article has no headlines, just paragraphs
        body[''] = paragraphs

        item['content'] = {'title': title, 'description': description, 'body':body}

        # There are no recommendations to other related articles
        item['recommendations'] = list()

        item['response_body'] = response.body
        
        yield item
