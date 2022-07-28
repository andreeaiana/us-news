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

class AxiosSpider(BaseSpider):
    """ Spider for Axios """
    name = 'axios'
    rotate_user_agent = True
    allowed_domains = ['www.axios.com']
    start_urls = ['https://www.axios.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.axios\.com\/\d+\/\d+\/\d+\/\w.*$'),
                    deny=(
                        r'www\.axios\.com\/pro\/\w.*',
                        r'www\.axios\.com\/newsletters',
                        r'www\.axios\.com\/about',
                        r'www\.axios\.com\/advertise',
                        r'www\.axios\.com\/careers',
                        r'www\.axios\.com\/events',
                        r'www\.axios\.com\/hbo',
                        r'www\.axios\.com\/legal',
                        r'www\.axios\.com\/contact',
                        r'www\.axios\.com\/app',
                        r'www\.axios\.com\/podcasts',
                        r'www\.axios\.com\/referral',
                        r'www\.axios\.com\/get-smart'
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

        creation_date = response.xpath('//meta[@property="article:published_time"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('T')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p | //ul/li[not(descendant::span)]')]
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

        item['news_outlet'] = 'axios'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@property="article:modified_time"]/@content').get()
        last_modified = datetime.fromisoformat(last_modified.split('T')[0])
        item['last_modified'] = last_modified.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//meta[@name="author"]/@content').get()
        if authors:
            authors = authors.split(',')
            item['author_person'] = [author for author in authors if author != 'Axios']  
            item['author_organization'] = ['Axios'] if 'Axios' in authors else list()
        else:
            item['author_person'] = list()
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
        recommendations = response.xpath('//a[@class="gtmContentClick"]/@data-vars-click-url').getall()
        item['recommendations'] = list(set([rec for rec in recommendations if 'www.axios.com' in rec]))[:5] if recommendations else list()

        item['response_body'] = response.body
        
        yield item
