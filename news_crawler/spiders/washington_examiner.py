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

class WashingtonExaminerSpider(BaseSpider):
    """ Spider for WashingtonExaminer """
    name = 'washington_examiner'
    rotate_user_agent = True
    allowed_domains = ['https://www.washingtonexaminer.com']
    start_urls = ['https://www.washingtonexaminer.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.washingtonexaminer\.com\/\w.*$'),
                    deny=(
                        r'newsletters\.washingtonexaminer\.com\/',
                        r'www\.washingtonexaminer\.com\/videos\/',
                        r'www\.washingtonexaminer\.com\/about\/',
                        r'www\.washingtonexaminer\.com\/editions\/',
                        r'www\.washingtonexaminer\.com\/staff\/',
                        r'www\.washingtonexaminer\.com\/sitemap\/',
                        r'www\.washingtonexaminer\.com\/contact\/',
                        r'www\.washingtonexaminer\.com\/careers\/',
                        r'www\.washingtonexaminer\.com\/terms\/',
                        r'www\.washingtonexaminer\.com\/policies-and-standards',
                        r'www\.washingtonexaminer\.com\/privacy-policy',
                        r'www\.washingtonexaminer\.com\/transparency-in-coverage'
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

        creation_date = response.xpath('//meta[@itemprop="datePublished"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('T')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(descendant::b/a[@class="Link"]) and not(descendant::b/u/a[@class="Link"]) and not(ancestor::div[@class="Enhancement"])]')]
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

        item['news_outlet'] = 'washington_examiner'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@itemprop="dateModified"]/@content').get()
        last_modified = datetime.fromisoformat(last_modified.split('T')[0])
        item['last_modified'] = last_modified.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        data_json = response.xpath('//script[@type="application/ld+json"]/text()').get()
        if data_json:
            data = json.loads(data_json)
            data_authors = data['author']
            authors = [author['name'] for author in data_authors]
            item['author_person'] = [author for author in authors if author!='Washington Examiner']
            item['author_organization'] = ['Washington Examiner'] if 'Washington Examiner' in authors else list()
        else:
            item['author_person'] = list()
            item['author_organization'] = list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//meta[@name="keywords"]/@content').get()
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
