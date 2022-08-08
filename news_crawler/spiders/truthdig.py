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

class TruthdigSpider(BaseSpider):
    """ Spider for Truthdig """
    name = 'truthdig'
    rotate_user_agent = True
    allowed_domains = ['www.truthdig.com']
    start_urls = ['https://www.truthdig.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.truthdig\.com\/\w.*$'),
                    deny=(
                        r'www\.truthdig\.com\/about-us\/',
                        r'www\.truthdig\.com\/events\/',
                        r'www\.truthdig\.com\/advertise\/',
                        r'www\.truthdig\.com\/jobs\/',
                        r'www\.truthdig\.com\/contact\/',
                        r'www\.truthdig\.com\/privacy-policy\/'
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

        creation_date = response.xpath('//time[@class="article-item__date"]/@datetime').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split(' ')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[contains(@class, "article-item__content")]/p[not(@*)] | //blockquote/p[not(@*)] | //div/p[@data-pp-blocktype="copy"]')]
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

        item['news_outlet'] = 'truthdig'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@property="article:modified_time"]/@content').get()
        last_modified = datetime.fromisoformat(last_modified.split('T')[0])
        item['last_modified'] = last_modified.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//h5[@class="people__name people__name--no-divider"]/text() | //h5[contains(@class, "people__name")]/a/text()').getall()
        if authors:
            authors = [author.strip() for author in authors]
            authors = [author for author in authors if author != '']
 
            author_person = authors[0]
            author_organization = [authors[-1].lstrip('/').strip()] if len(authors) == 2 else list()
            
            author_person = author_person.split(' and ') if ' and ' in author_person else [author_person]
            if author_organization:
                item['author_person'] = [author.rstrip('/').strip() for author in author_person]
                item['author_organization'] = author_organization
            else:
                processed_author_person = list()
                for author in author_person:
                    if not '/' in author:
                        processed_author_person.append(author)
                    else:
                        person, organization = author.split('/') 
                        if person != '':
                            processed_author_person.append(person.strip())
                        if organization != '':
                            author_organization.append(organization.strip())
                item['author_person'] = processed_author_person
                item['author_organization'] = author_organization
        else:
            item['author_person'] = list()
            item['author_organization'] = list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//div[@class="tags-list__list"]/a[@rel="tag"]/text()').getall()
        item['news_keywords'] = news_keywords if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@name="description"]/@content').get().strip()

         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        if response.xpath('//h2[not(@*)]'):
            # Extract headlines
            headlines = [h2.xpath('string()').get().strip() for h2 in response.xpath('//h2[not(@*)]')]

            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div[contains(@class, "article-item__content")]/p[not(@*)] | //blockquote/p[not(@*)] | //div/p[@data-pp-blocktype="copy"] | //h2[not(@*)]')]

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
