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

class PoliticoSpider(BaseSpider):
    """ Spider for Politico"""
    name = 'politico'
    rotate_user_agent = True
    allowed_domains = ['www.politico.com']
    start_urls = ['https://www.politico.com/']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.politico\.com\/news.*\/\w.*$'),
                    deny=(
                        r'www\.politico\.com\/minutes\/congress\/\w.*$',
                        r'www\.politicopro\.com',
                        r'www\.politico\.com\/about\-us',
                        r'www\.politico\.com\/advertising',
                        r'www\.politico\.com\/subscribe\/breaking-news-alerts',
                        r'www\.politico\.com\/careers',
                        r'www\.politico\.com\/payment',
                        r'www\.politico\.com\/feedback',
                        r'www\.politico\.com\/gallery',
                        r'www\.politico\.com\/faq',
                        r'www\.politico\.com\/press\/about',
                        r'www\.politico\.com\/rss',
                        r'www\.politico\.com\/subscriptions',
                        r'www\.politico\.com\/corrections',
                        r'www\.politico\.com\/sitemap',
                        r'www\.politico\.com\/write\-for\-us',
                        r'www\.politico\.com\/terms\-of\-service',
                        r'www\.politico\.com\/do\-not\-sell',
                        r'www\.politico\.com\/privacy\-policy',
                        r'www\.politico\.com\/privacy'
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
        creation_date = datetime.fromisoformat(creation_date)
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[contains(@class, "story-text__paragraph   ")] | //p[not(@*)]')]
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

        item['news_outlet'] = 'politico'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = [node.xpath('string()').get().strip() for node in response.xpath('//p[@class="story-meta__authors"]/span/a')]
        if not authors:
            authors = response.xpath('//div[@itemprop="author"]/meta[@itemprop="name"]/@content').getall()
        
        if authors:
            if not "Associated Press" in authors:
                item['author_person'] = [author for author in authors]
                item['author_organization'] = list()
            else:
                item['author_person'] = list()
                item['author_organization'] = [author for author in authors]
        else:
            item['author_person'] = list()
            item['author_organization'] = list()

        # Extract keywords, if available
        news_keywords = [node.xpath('string()').get().strip() for node in response.xpath('//ul[@role="list" and @aria-label="Filed Under:"]/li[@class="story-tags__list-item"]/a | //ul[@class="categories-list"]/li/a')]
        item['news_keywords'] = news_keywords if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@property="og:description"]/@content').get()
        description = description.strip() if description else ''        

         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        if response.xpath('//h3[contains(@class, "story-text__heading")] | //header[@class="block-header"]/h2'):
            # Extract headlines
            headlines = [h3.xpath('string()').get().strip() for h3 in response.xpath('//h3[contains(@class, "story-text__heading")] | //header[@class="block-header"]/h2')]

            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//p[contains(@class, "story-text__paragraph   ")] | //p[not(@*)] | //h3[contains(@class, "story-text__heading")] | //header[@class="block-header"]/h2')]

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
