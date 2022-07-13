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

class NYPostSpider(BaseSpider):
    """ Spider for New York Post """
    name = 'nypost'
    rotate_user_agent = True
    allowed_domains = ['nypost.com']
    start_urls = ['https://nypost.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'nypost\.com\/\d+\/\d+\/\d+\/\w.*\/$'),
                    deny=(
                        r'nypost\.com\/tips\/',
                        r'nypost\.com\/video\/',
                        r'nypost\.com\/astrology\/',
                        r'nypost\.com\/photos\/',
                        r'nypost\.com\/covers\/',
                        r'nypost\.com\/columnists\/',
                        r'nypost\.com\/horoscopes\/',
                        r'nypost\.com\/odds\/',
                        r'nypost\.com\/podcasts\/',
                        r'nypost\.com\/careers\/',
                        r'nypost\.com\/accout\/',
                        r'nypost\.com\/contact\/',
                        r'nypost\.com\/terms\/',
                        r'nypost\.com\/privacy\/',
                        r'nypost\.com\/sitemap\/',
                        r'nypost\.com\/sports-plus\/',
                        r'nypost\.com\/rssfeeds\/',
                        r'nypost\.com\/home-delivery\/',
                        r'nypost\.com\/about-new-york-post\/',
                        r'nypost\.com\/customer-service\/',
                        r'nypost\.com\/community-guidelines\/',
                        r'nypost\.com\/membership-terms\/',
                        r'nypost\.com\/ca-privacy-rights\/'
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
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(@*)]')]
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

        item['news_outlet'] = 'nypost'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@property="article:modified_time"]/@content').get()
        last_modified = datetime.fromisoformat(last_modified.split('T')[0])
        item['last_modified'] = last_modified.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//div[@class="byline__author"]/a/text() | //div[@class="byline__author"]/span/text()').getall()
        if authors:
            item['author_person'] = [author for author in authors if author != 'Post Editorial Board']
            item['author_organization'] = ['Post Editorial Board'] if 'Post Editorial Board' in authors else list()
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
        recommendations = response.xpath('//div[@class="inline-module inline-module--related-post"]//a/@href').getall()
        item['recommendations'] = list(set(recommendations))[:5] if recommendations else list()

        item['response_body'] = response.body
        
        yield item
