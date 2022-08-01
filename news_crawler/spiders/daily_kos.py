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

class DailyKosSpider(BaseSpider):
    """ Spider for Daily Kos """
    name = 'daily_kos'
    rotate_user_agent = True
    allowed_domains = ['www.dailykos.com']
    start_urls = ['https://www.dailykos.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.dailykos\.com\/stories\/\d+\/\d+\/\d+\/\w.*$'),
                    deny=(
                        r'www\.dailykos\.com\/jobs\/',
                        r'www\.dailykos\.com\/contactus\/',
                        r'www\.dailykos\.com\/advertising\/',
                        r'www\.dailykos\.com\/privacy',
                        r'www\.dailykos\.com\/terms',
                        r'www\.dailykos\.com\/about-us',
                        r'www\.dailykos\.com\/dmca-copyright-notice',
                        r'www\.dailykos\.com\/rules-of-the-road'
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

        creation_date = response.xpath('//div[@class="author-date visible-sm-block"]/span/text()').get()
        if not creation_date:
            return
        creation_date = datetime.strptime(creation_date, '%Y/%m/%d')
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

        item['news_outlet'] = 'daily_kos'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        author_person = response.xpath('//div[@class="author-byline name-heading"]/span[@class="author-name"]/a/text()').get()
        author_organization = response.xpath('//div[@class="author-byline designation"]/span/text()').get()
        item['author_person'] = [author_person] if author_person else list()
        item['author_organization'] = [author_organization] if author_organization else list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//div[@class="story-tags-wrapper"]/ul/li/a[@class="tag-name"]/text()').getall()
        item['news_keywords'] = news_keywords if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@name="description"]/@content').get().strip()

         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        if response.xpath('//h3[not(@*)]'):
            # Extract headlines
            headlines = [h3.xpath('string()').get().strip() for h3 in response.xpath('//h3[not(@*)]')]

            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(@*)] | //h3[not(@*)]')]

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
