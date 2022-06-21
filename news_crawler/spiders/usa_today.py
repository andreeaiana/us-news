# -*- coding: utf-8 -*-

import os
import sys
import json
import unicodedata
from news_crawler.spiders import BaseSpider
from scrapy.spiders import Rule 
from scrapy.linkextractors import LinkExtractor
from datetime import datetime

sys.path.insert(0, os.path.join(os.getcwd(), "..",))
from news_crawler.items import NewsCrawlerItem
from news_crawler.utils import remove_empty_paragraphs

class USATodaySpider(BaseSpider):
    """ Spider for USA Today"""
    name = 'usa_today'
    rotate_user_agent = True
    allowed_domains = ['eu.usatoday.com']
    start_urls = ['https://eu.usatoday.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'eu\.usatoday\.com\/story\/\w.*$'),
                    deny=(
                        r'games\.usatoday\.com\/\w.*',
                        r'profile\.usatoday\.com\/newsletters',
                        r'supportlocal\.usatoday\.com',
                        r'coupons\.usatoday\.com',
                        r'eu\.usatoday\.com\/media',
                        r'eu\.usatoday\.com',
                        r'cm\.usatoday\.com'
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

        creation_date = response.xpath('//div[@class="publish-date"]/lit-timestamp/@publishdate').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('T')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(child::span) and not(child::em)] | //ul[preceding::p[not(child::span) and not(child::em)]]/li[not(@class)]')]
        paragraphs = [unicodedata.normalize('NFKD', paragraph) for paragraph in paragraphs]
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

        item['news_outlet'] = 'usa_today'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//div/span[@class="author"]/a/text()').getall()
        item['author_person'] = [author for author in authors] if authors else list()
        item['author_organization'] = list()
       
        # Extract keywords, if available
        data_json = response.xpath('//script[@type="application/json"]/text()').get()
        if data_json:
            data = json.loads(data_json)
            news_keywords = data['keywords']
            item['news_keywords'] = [keyword for keyword in news_keywords if keyword!=''] 
        else:
            item['news_keywords'] = list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@name="description"]/@content').get().strip()

         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        if response.xpath('//h2'):
            # Extract headlines
            headlines = [h2.xpath('string()').get().strip() for h2 in response.xpath('//h2')]
            headlines = [h for h in headlines if h!='']

            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(child::span) and not(child::em)] | //ul[preceding::p[not(child::span) and not(child::em)]]/li[not(@class)] | //h2')]
            text = [unicodedata.normalize('NFKD', paragraph) for paragraph in text]

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
