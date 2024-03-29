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

class InsiderSpider(BaseSpider):
    """ Spider for Insider"""
    name = 'insider'
    rotate_user_agent = True
    allowed_domains = ['www.insider.com']
    start_urls = ['https://www.insider.com/']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.insider\.com\/\w.*$'),
                    deny=(
                        r'www\.insider\.com\/contact',
                        r'www\.insider\.com\/sitemap\/index',
                        r'www\.businessinsider\.com'
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

        creation_date = response.xpath('//meta[@name="date"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date)
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div/p[not(@class)]')]
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

        item['news_outlet'] = 'insider'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@name="lastmod"]/@content').get()
        item['last_modified'] = datetime.fromisoformat(last_modified.split('T')[0]).strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//meta[@property="author"]/@content').get()
        item['author_person'] = authors.split(', ')
        item['author_organization'] = list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//meta[@name="news_keywords"]/@content').get()
        item['news_keywords'] = news_keywords.split(', ')

        # Get title, description, and body of article
        title = response.xpath('//meta[@name="title"]/@content').get().strip()
        description = response.xpath('//meta[@name="description"]/@content').get().strip()

         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        if response.xpath('//h2'):
            # Extract headlines
            headlines = [h2.xpath('string()').get().strip() for h2 in response.xpath('//h2')]

            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div/p[not(@class)] | //h2')]

            # Extract paragraphs between the abstract and the first headline
            body[''] = remove_empty_paragraphs(text[:text.index(headlines[0])])

            # Extract paragraphs corresponding to each headline, except the last one
            for i in range(len(headlines)-1):
                body[headlines[i]] = remove_empty_paragraphs(text[text.index(headlines[i])+1:text.index(headlines[i+1])])

            # Extract the paragraphs belonging to the last headline
            body[headlines[-1]] = remove_empty_paragraphs(text[text.index(headlines[-1])+1:])

        else:
            # The article has no headlines, just paragraphs
            body[''] = paragraphs

        item['content'] = {'title': title, 'description': description, 'body':body}

        # There are no recommendations to other related articles
        item['recommendations'] = list()

        item['response_body'] = response.body
        
        yield item
