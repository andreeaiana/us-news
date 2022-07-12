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

class FoxNewsSpider(BaseSpider):
    """ Spider for Fox News Channel """
    name = 'fox_news'
    rotate_user_agent = True
    allowed_domains = ['www.foxnews.com']
    start_urls = ['https://www.foxnews.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.foxnews\.com\/\w.*\/\w.*$'),
                    deny=(
                        r'www\.foxnews\.com\/shows',
                        r'www\.foxnews\.com\/contact',
                        r'www\.foxnews\.com\/compliance',
                        r'www\.foxnews\.com\/donotsell',
                        r'www\.foxnews\.com\/terms-of-use',
                        r'www\.foxnews\.com\/privacy-policy',
                        r'www\.foxnews\.com\/story\/where-in-the-world-is-fox'
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

        creation_date = response.xpath('//meta[@name="dcterms.created"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('T')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(descendant::a[@target="_blank"]/strong) and not(descendant::i) and not(@class="copyright") and not(@class="dek") and not(@class="subscribed hide") and not(@class="success hide") and not(@data-v-a7f268cc) and not(ancestor::div[@class="caption"])]')]
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

        item['news_outlet'] = 'fox_news'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@name="dcterms.modified"]/@content').get()
        last_modified = datetime.fromisoformat(last_modified.split('T')[0])
        item['last_modified'] = last_modified.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//div[contains(@class, "author-byline")]//span/a/text()').getall()
        item['author_person'] = [author for author in authors if author != ' | Fox News'] if authors else list() 
        item['author_organization'] = ['Fox News'] if ' | Fox News' in authors else list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//meta[@name="classification-tags"]/@content').get()
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
        item['recommendations'] = list()

        item['response_body'] = response.body
        
        yield item
