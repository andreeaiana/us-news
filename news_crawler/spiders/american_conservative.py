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

class AmericanConservativeSpider(BaseSpider):
    """ Spider for The American Conservative """
    name = 'american_conservative'
    rotate_user_agent = True
    allowed_domains = ['www.theamericanconservative.com']
    start_urls = ['https://www.theamericanconservative.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.theamericanconservative\.com\/\w.*$'),
                    deny=(
                        r'www\.theamericanconservative\.com\/donate\/',
                        r'www\.theamericanconservative\.com\/about-us\/',
                        r'www\.theamericanconservative\.com\/writers\/',
                        r'www\.theamericanconservative\.com\/event\/',
                        r'www\.theamericanconservative\.com\/podcast\/',
                        r'www\.theamericanconservative\.com\/video\/',
                        r'www\.theamericanconservative\.com\/contact-us\/',
                        r'www\.theamericanconservative\.com\/subscribe\/',
                        r'www\.theamericanconservative\.com\/advertise\/',
                        r'www\.theamericanconservative\.com\/frequently-asked-questions\/',
                        r'www\.theamericanconservative\.com\/comments-policy\/',
                        r'www\.theamericanconservative\.com\/privacy-policy\/'
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
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//main[@class="c-blog-post__body"]//div/p | //blockquote[@class="wp-block-quote"]/p')]
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

        item['news_outlet'] = 'american_conservative'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@property="article:modified_time"]/@content').get()
        last_modified = datetime.fromisoformat(last_modified.split('T')[0])
        item['last_modified'] = last_modified.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//div[@class="o-byline__authors"]/a/text()').getall()
        item['author_person'] = [author.strip() for author in authors] if authors else list()
        item['author_organization'] = list()
       
        # Extract keywords, if available
        data_json = response.xpath('//script[@type="application/ld+json"]/text()').get()
        if data_json:
            data = json.loads(data_json)
            if 'keywords' in data['@graph'][-2].keys():
                news_keywords = data['@graph'][-2]['keywords']
                item['news_keywords'] = news_keywords if news_keywords else list()
            else:
                item['news_keywords'] = list()
        else:
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
