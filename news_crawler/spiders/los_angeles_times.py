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

class LATimesSpider(BaseSpider):
    """ Spider for Los Angeles Times """
    name = 'los_angeles_times'
    rotate_user_agent = True
    allowed_domains = ['www.latimes.com']
    start_urls = ['https://www.latimes.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.latimes\.com\/\w.*\/story\/\w.*$'),
                    deny=(
                        r'www\.latimes\.com\/espanol\/',
                        r'www\.latimes\.com\/california\/photography',
                        r'www\.latimes\.com\/podcasts',
                        r'www\.latimes\.com\/video',
                        r'www\.latimes\.com\/about',
                        r'www\.latimes\.com\/games',
                        r'www\.latimes\.com\/bestcovery\/',
                        r'www\.latimes\.com\/b2bpublishing',
                        r'www\.latimes\.com\/b2b\/',
                        r'www\.latimes\.com\/brandpublishing\/hotproperty',
                        r'www\.latimes\.com\/events-los-angeles-times',
                        r'www\.latimes\.com\/specialsupplements',
                        r'www\.latimes\.com\/terms-of-service',
                        r'www\.latimes\.com\/privacy-policy'
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

        creation_date = response.xpath('//time[@class="published-date"]/@datetime').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('T')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="page-article-body"]//p[not(@*)]')]
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

        item['news_outlet'] = 'los_angeles_times'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//div[@class="authors"]/div[@class="author-name"]/a[@data-click="standardBylineAuthorName"]/text() | //div[@class="authors"]/div[@class="author-name"]/span[@class="link"]/text() | //div[@class="authors-byline"]/div[@class="authors-byline-text"]/span[@class="author-name"]/a/text()').getall()
        item['author_person'] = [author for author in authors if author != 'The Times Editorial Board'] if authors else list()
        item['author_organization'] = ['The Times Editorial Board'] if authors and 'The Times Editorial Board' in authors else list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//div[@class="tags"]/a/text()').getall()
        item['news_keywords'] = news_keywords if news_keywords else list()

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
