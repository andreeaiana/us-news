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

class HillSpider(BaseSpider):
    """ Spider for The Hill"""
    name = 'hill'
    rotate_user_agent = True
    allowed_domains = ['thehill.com']
    start_urls = ['https://thehill.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'thehill\.com\/\w.*$'),
                    deny=(
                        r'thehill\.com\/people',
                        r'thehill\.com\/events',
                        r'thehill\.com\/hilltv',
                        r'thehill\.com\/contact',
                        r'thehill\.com\/video/',
                        r'thehill\.com\/submitting-opinion-content',
                        r'thehill\.com\/events-about',
                        r'thehill\.com\/hill-apps',
                        r'thehill\.com\/resources\/rss-feeds',
                        r'thehill\.com\/resources\/classifieds\/employer',
                        r'thehill\.com\/changing-america'
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

        creation_date = response.xpath('//meta[@name="dcterms.date"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('T')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[contains(@class, "article__text")]/p[not(child::strong)]')]
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

        item['news_outlet'] = 'hill'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//meta[@name="dcterms.creator"]/@content').get()
        if authors:
            authors = authors.split(', ')
            authors = [author for author in authors if not 'opinion contributor' in author]
        else:
            authors = list()
        item['author_person'] = authors
        item['author_organization'] = list()
       
        # Extract keywords, if available
        news_keywords = [node.xpath('string()').get().strip() for node in response.xpath('//section[@class="text-300 text-transform-upper"]//a')]
        item['news_keywords'] = news_keywords if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@name="dcterms.title"]/@content').get().strip()
        description = response.xpath('//meta[@name="dcterms.description"]/@content').get().strip()

         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        if response.xpath('//h2[not(@class)]'):
            # Extract headlines
            headlines = [h2.xpath('string()').get().strip() for h2 in response.xpath('//h2[not(@class)]')]

            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div[contains(@class, "article__text")]/p[not(child::strong)] | //h2[not(@class)]')]

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
