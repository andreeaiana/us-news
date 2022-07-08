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

class CBNSpider(BaseSpider):
    """ Spider for CBN """
    name = 'cbn'
    rotate_user_agent = True
    allowed_domains = ['www1.cbn.com']
    start_urls = ['https://www1.cbn.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www1\.cbn\.com\/cbnnews\/\w.*$'),
                    deny=(
                        r'www1\.cbn\.com\/about\/\w.*$',
                        r'www1\.cbn\.com\/cbnnews\/video\/',
                        r'www1\.cbn\.com\/prayer',
                        r'www1\.cbn\.com\/radio',
                        r'www1\.cbn\.com\/devotions',
                        r'www1\.cbn\.com\/contact',
                        r'www1\.cbn\.com\/cbn-partners',
                        r'www1\.cbn\.com\/cbn-apps',
                        r'www1\.cbn\.com\/job-openings',
                        r'www1\.cbn\.com\/terms-of-use',
                        r'www1\.cbn\.com\/social-networks',
                        r'www1\.cbn\.com\/cbn-donor-privacy-policy',
                        r'www1\.cbn\.com\/cbn-cookies-policy',
                        r'www1\.cbn\.com\/cbn-third-party-processor-information'
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

        creation_date = response.xpath('//meta[@name="published_at"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('T')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="field-name-body"]//p[not(descendant::em/strong) and not(descendant::strong/em)]')]
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

        item['news_outlet'] = 'cbn'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//div[@property="schema:author"]/a/text()').getall()
        item['author_person'] = authors if authors else list()
        item['author_organization'] = list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//meta[@name="keywords"]/@content').getall()
        item['news_keywords'] = news_keywords if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@property="og:description"]/@content').get().strip()

         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        # The article has no headlines, just paragraphs
        body[''] = paragraphs

        item['content'] = {'title': title, 'description': description, 'body':body}

        # There are no recommendations to other related articles
        item['recommendations'] = list()

        item['response_body'] = response.body
        
        yield item
