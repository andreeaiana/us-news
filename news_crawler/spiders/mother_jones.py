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

class MotherJonesSpider(BaseSpider):
    """ Spider for Mother Jones """
    name = 'mother_jones'
    rotate_user_agent = True
    allowed_domains = ['www.motherjones.com']
    start_urls = ['https://www.motherjones.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.motherjones\.com\/\w.*\/\d+\/\d+\/\w.*$'),
                    deny=(
                        r'www\.motherjones\.com\/newsletters\/',
                        r'www\.motherjones\.com\/about\/',
                        r'www\.motherjones\.com\/jobs\/',
                        r'www\.motherjones\.com\/events\/',
                        r'www\.motherjones\.com\/contact\/',
                        r'www\.motherjones\.com\/support\/',
                        r'www\.motherjones\.com\/advertising\/',
                        r'www\.motherjones\.com\/podcasts\/',
                        r'www\.motherjones\.com\/customer-service\/'
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

        creation_date = response.xpath('//meta[@property="article:published"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('T')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//*[@id="fullwidth-body"]/p | //*[contains(@id, "post-")]/article/p | //ol/li')]
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

        item['news_outlet'] = 'mother_jones'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@property="article:modified"]/@content').get()
        last_modified = datetime.fromisoformat(last_modified.split('T')[0])
        item['last_modified'] = last_modified.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//meta[@property="article:author"]/@content').getall()
        item['author_person'] = authors if authors else list() 
        item['author_organization'] = list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//meta[@property="article:tag"]/@content').getall()
        item['news_keywords'] = news_keywords if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@property="og:description"]/@content').get().strip()

         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        # The article has no headlines, just paragraphs
        body[''] = paragraphs

        item['content'] = {'title': title, 'description': description, 'body':body}

        # Recommendations to top 5 other related articles from the same outlet
        recommendations = response.xpath('//li/div/a[contains(@data-ga-label, "RelatedArticle") and contains(@data-ga-label, "headline")]/@data-ga-action').getall()
        item['recommendations'] = recommendations[:5] if recommendations else list()

        item['response_body'] = response.body
        
        yield item
