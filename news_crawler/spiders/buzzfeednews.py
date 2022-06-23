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

class BuzzfeednewsSpider(BaseSpider):
    """ Spider for BuzzfeednewsSpider """
    name = 'buzzfeednews'
    rotate_user_agent = True
    allowed_domains = ['www.buzzfeednews.com']
    start_urls = ['https://www.buzzfeednews.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.buzzfeednews\.com\/article\/\w.*$'),
                    deny=(
                        r'www\.buzzfeednews\.com\/article\/buzzfeednews\/about-buzzfeed-news',
                        r'tips\.buzzfeednews\.com\/',
                        r'support\.buzzfeednews\.com\/'
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

        creation_date = response.xpath('//span[contains(@class, "headline-timestamp_timestampNews")]/time/@datetime').get()
        if not creation_date:
            creation_date = response.xpath('//div/p[@class="news-article-header__timestamps-posted"]/text()').get()
            creation_date = creation_date.strip().split('Posted on ')[1].split(', at')[0]
            if not creation_date:
                return
            else:
                creation_date = datetime.strptime(creation_date, '%B %d, %Y')
        else:
            creation_date = datetime.fromisoformat(creation_date.split('T')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(ancestor::div[contains(@class, "subbuzz__description")]) and not(@class) and not(ancestor::span[@class="FF__grid-cred"])] | //ul/li/p')]
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

        item['news_outlet'] = 'buzzfeednews'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//meta[@property="author"]/@content').get()
        if authors:
            item['author_person'] = authors.split(', ')
        else:
            authors = response.xpath('//div[contains(@class, "news-article-header")]/p/a/text()').getall()
            item['author_person'] = authors if authors else list()
        item['author_organization'] = list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//ul[preceding-sibling::h2[contains(@class, "topic-tags_heading")]]/li/a/text()').getall()
        item['news_keywords'] = news_keywords if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@name="description"]/@content').get().strip()

         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        if response.xpath('//h2/span[@class="js-subbuzz__title-text"]'):
            # Extract headlines
            headlines = [h.xpath('string()').get().strip() for h in response.xpath('//h2/span[@class="js-subbuzz__title-text"]')]

            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(ancestor::div[contains(@class, "subbuzz__description")]) and not(@class) and not(ancestor::span[@class="FF__grid-cred"])] | //ul/li/p | //h2/span[@class="js-subbuzz__title-text"]')]

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

        # Top 5 recommendations to other related news articles from the same outlet
        recommendations = response.xpath('//li[@class="bfp-related-links__list-item"]/div/a/@href').getall()
        if recommendations:
            item['recommendations'] = list(set(recommendations))[:5]
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body
        
        yield item
