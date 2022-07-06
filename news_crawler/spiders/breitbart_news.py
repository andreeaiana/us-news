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

class BreaitbartNewsSpider(BaseSpider):
    """ Spider for Breaitbart News` """
    name = 'breitbart_news'
    rotate_user_agent = True
    allowed_domains = ['www.breitbart.com']
    start_urls = ['https://www.breitbart.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.breitbart\.com\/\w.*\/\d+\/\d+\/\d+\/\w.*$'),
                    deny=(
                        r'www\.breitbart\.com\/masthead\/',
                        r'www\.breitbart\.com\/mediakit\/',
                        r'www\.breitbart\.com\/jobs\/',
                        r'www\.breitbart\.com\/video\/',
                        r'www\.breitbart\.com\/newsetters\/',
                        r'www\.breitbart\.com\/people\/',
                        r'www\.breitbart\.com\/accessibility-statement\/',
                        r'www\.breitbart\.com\/policy-information\/',
                        r'www\.breitbart\.com\/terms-of-use\/',
                        r'www\.breitbart\.com\/privacy-policy\/',
                        r'www\.breitbart\.com\/contact-us\/',
                        r'www\.breitbart\.com\/send-a-tip\/',
                        r'www\.breitbart\.com\/navigational-sitemap\/',
                        r'www\.breitbart\.com\/podcasts\/'
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

        creation_date = response.xpath('//meta[@name="pubdate"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('T')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="entry-content"]/p')]
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

        item['news_outlet'] = 'breitbart_news'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@name="lastmod"]/@content').get()
        last_modified = datetime.fromisoformat(last_modified.split('T')[0])
        item['last_modified'] = last_modified.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//meta[@name="author"]/@content').get()
        if authors:
            authors = authors.split(' and ')
            item['author_person'] = [author for author in authors if author != 'AP'] 
            item['author_organization'] = ['AP'] if 'AP' in authors else list()
        else:
            item['author_person'] = list()
            item['author_organization'] = list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//meta[@property="article:tag"]/@content').getall()
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
