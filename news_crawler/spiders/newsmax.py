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

class NewsmaxSpider(BaseSpider):
    """ Spider for Newsmax """
    name = 'newsmax'
    rotate_user_agent = True
    allowed_domains = ['www.newsmax.com']
    start_urls = ['https://www.newsmax.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.newsmax\.com\/\w.*\/\w.*$'),
                    deny=(
                        r'www\.newsmax\.com\/contact\/',
                        r'www\.newsmax\.com\/rss\/',
                        r'www\.newsmax\.com\/archives\/',
                        r'www\.newsmax\.com\/advertise\/',
                        r'www\.newsmax\.com\/links\/',
                        r'www\.newsmax\.com\/platinum\/',
                        r'www\.newsmax\.com\/books\/',
                        r'www\.newsmax\.com\/newsmaxbest\/',
                        r'www\.newsmax\.com\/privacystatement\/',
                        r'www\.newsmax\.com\/termsconditions\/'
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
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@itemprop="articleBody"]/p | //div[@itemprop="articleBody"]/p/strong')]
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

        item['news_outlet'] = 'newsmax'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//meta[@property="article:author"]/@content').getall()
        item['author_person'] = authors if authors else list()
        item['author_organization'] = list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//meta[@name="news_keywords"]/@content').get()
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
        recommendations = response.xpath('//div[@id="divArticleRelatedStories"]/ul/li//a/@href').getall()
        item['recommendations'] = recommendations[:5] if recommendations else list()

        item['response_body'] = response.body
        
        yield item
