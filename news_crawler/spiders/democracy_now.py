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

class DemocracyNowSpider(BaseSpider):
    """ Spider for Democracy Now """
    name = 'democracy_now'
    rotate_user_agent = True
    allowed_domains = ['www.democracynow.org']
    start_urls = ['https://www.democracynow.org']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.democracynow\.org\/\d+\/\d+\/\d+\/\w.*$'),
                    deny=(
                        r'www\.democracynow\.org\/about',
                        r'www\.democracynow\.org\/subscribe',
                        r'www\.democracynow\.org\/events',
                        r'www\.democracynow\.org\/es',
                        r'www\.democracynow\.org\/stations',
                        r'www\.democracynow\.org\/get_involved',
                        r'www\.democracynow\.org\/contact',
                        r'www\.democracynow\.org\/education',
                        r'www\.democracynow\.org\/pages\/help\/podcasting'
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

        creation_date = response.xpath('//div[@id="story_content"]//span[@class="date"]/text()').get()
        if not creation_date:
            return
        creation_date = datetime.strptime(creation_date, '%B %d, %Y')
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(descendant::span[@class="plea"])]')]
        paragraphs = paragraphs[:-1]
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

        item['news_outlet'] = 'democracy_now'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        item['author_person'] = list()
        item['author_organization'] = list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//a[@data-ga-action="Story: Topic"]/text()').getall()
        item['news_keywords'] = list(set(news_keywords)) if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@property="og:description"]/@content').get().strip()

         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        # The article has no headlines, just paragraphs
        body[''] = paragraphs

        item['content'] = {'title': title, 'description': description, 'body':body}

        # Recommendations to top 5 other related articles from the same outlet
        recommendations = response.xpath('//a[@data-ga-action="Story: Recommended"]/@href').getall()
        if recommendations:
            recommendations = list(set(recommendations))
            recommendations = ['www.democracynow.org' + rec for rec in recommendations]
            item['recommendations'] = recommendations[:5]
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body
        
        yield item
