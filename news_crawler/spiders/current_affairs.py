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

class CurrentAffairsSpider(BaseSpider):
    """ Spider for Current Affairs """
    name = 'current_affairs'
    rotate_user_agent = True
    allowed_domains = ['www.currentaffairs.org']
    start_urls = ['https://www.currentaffairs.org']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.currentaffairs\.org\/\d+\/\d+\/\w.*$'),
                    deny=(
                        r'www\.currentaffairs\.org\/\d+\/\d+\/about-us\/',
                        r'www\.currentaffairs\.org\/\d+\/\d+\/privacy-policy\/',
                        r'www\.currentaffairs\.org\/store',
                        r'www\.currentaffairs\.org\/donate',
                        r'www\.currentaffairs\.org\/subscribe'
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

        creation_date = response.xpath('//mark[@class="dateline"]/span/text()').get()
        if not creation_date:
            return
        creation_date = creation_date.lstrip('filed ').rstrip(' in')
        creation_date = datetime.strptime(creation_date, '%d %B %Y')
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//section[contains(@class, "essay-block")]/p | //h3/strong')]
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

        item['news_outlet'] = 'current_affairs'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//div[@class="bylines"]/ul/li/a[contains(@href, "/author/")]/text()').getall()
        item['author_person'] = [author for author in authors if author != 'Current Affairs'] if authors else list()
        item['author_organization'] = ['Current Affairs'] if authors and 'Current Affairs' in authors else list()
       
        # Extract keywords, if available
        item['news_keywords'] = list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@name="description"]/@content').get().strip()
        description = description.lstrip('<p>').rstrip(' </p>')

         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        if response.xpath('//h2[not(@*) and not(ancestor::div[@class="teaser"])]'):
            # Extract headlines
            headlines = [h2.xpath('string()').get().strip() for h2 in response.xpath('//h2[not(@*) and not(ancestor::div[@class="teaser"])]')]

            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//section[contains(@class, "essay-block")]/p | //h3/strong | //h2[not(@*) and not(ancestor::div[@class="teaser"])]')]

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
