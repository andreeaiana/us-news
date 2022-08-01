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

class RedneckRevoltSpider(BaseSpider):
    """ Spider for Redneck Revolt """
    name = 'redneck_revolt'
    rotate_user_agent = True
    allowed_domains = ['www.redneckrevolt.org']
    start_urls = ['https://www.redneckrevolt.org']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.redneckrevolt\.org\/single-post\/\d+\/\d+\/\d+\/\w.*$'),
                    deny=(
                        r'www\.redneckrevolt\.org\/about',
                        r'www\.redneckrevolt\.org\/principles',
                        r'www\.redneckrevolt\.org\/podcast',
                        r'www\.redneckrevolt\.org\/support',
                        r'www\.redneckrevolt\.org\/press-kit',
                        r'www\.redneckrevolt\.org\/printable-resources'
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
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[@id]/span')]
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

        item['news_outlet'] = 'redneck_revolt'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@property="article:modified_time"]/@content').get()
        last_modified = datetime.fromisoformat(last_modified.split('T')[0])
        item['last_modified'] = last_modified.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//meta[@property="article:author"]/@content').get()
        if authors:
            if ' and ' in authors:
                authors, last_author = authors.split(' and ')
                authors = authors.split(', ')
                authors.append(last_author)
            else:
                authors = authors.split(', ')
            item['author_person'] = [author for author in authors if author != 'Redneck Revolt']
            item['author_organization'] = ['Redneck Revolt'] if 'Redneck Revolt' in authors else list()
        else:
            item['author_person'] = list()
            item['author_organization'] = list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//nav[@aria-label="tags" and preceding-sibling::p[@class="fxkqDZ"]]/ul/li/a/text()').getall()
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
