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

class NewsweekSpider(BaseSpider):
    """ Spider for Newsweek """
    name = 'newsweek'
    rotate_user_agent = True
    allowed_domains = ['www.newsweek.com']
    start_urls = ['https://www.newsweek.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.newsweek\.com\/\w.*$'),
                    deny=(
                        r'www\.newsweek\.com\/podcasts',
                        r'www\.newsweek\.com\/announcements',
                        r'www\.newsweek\.com\/careers',
                        r'www\.newsweek\.com\/corrections',
                        r'www\.newsweek\.com\/contact',
                        r'www\.newsweek\.com\/copyright',
                        r'www\.newsweek\.com\/about-newsweek',
                        r'www\.newsweek\.com\/editorial-guidelines',
                        r'www\.newsweek\.com\/mission-statement',
                        r'www\.newsweek\.com\/terms-service',
                        r'www\.newsweek\.com\/privacy-policy',
                        r'www\.newsweek\.com\/cookie-policy',
                        r'www\.newsweek\.com\/terms-sale',
                        r'newsweek\.com\/advertise',
                        r'subscribe\.newsweek\.com\/product'
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
        creation_date = datetime.fromisoformat(creation_date.split('T')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(@class="copyright")]')]
        paragraphs = remove_empty_paragraphs(paragraphs)
        paragraphs = paragraphs[:-1] # Remove advertisement in last line
        text = ' '.join([para for para in paragraphs])

        # Check article's length validity
        if not self.has_min_length(text):
            return

        # Check keywords validity
        if not self.has_valid_keywords(text):
            return

        # Parse the valid article
        item = NewsCrawlerItem()

        item['news_outlet'] = 'newsweek'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//span[@class="author"]/a/text() | //span[@class="author"]/span/text()').get()
        item['author_person'] = [author.strip() for author in authors.split(' and ')] if authors else list()
        item['author_organization'] = list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//meta[@name="news_keywords"]/@content').get()
        item['news_keywords'] = news_keywords.split(',') if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@name="description"]/@content').get().strip()

         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        if response.xpath('//h2 | //h3'):
            # Extract headlines
            headlines = [h.xpath('string()').get().strip() for h in response.xpath('//h2 | //h3')]

            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(@class="copyright")] | //h2 | //h3')]
            text = text[:-1] # Remove advertisement in last line

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
