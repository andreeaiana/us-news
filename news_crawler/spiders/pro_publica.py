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

class ProPublicaSpider(BaseSpider):
    """ Spider for ProPublica """
    name = 'pro_publica'
    rotate_user_agent = True
    allowed_domains = ['www.propublica.org']
    start_urls = ['https://www.propublica.org']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.propublica\.org\/article\/\w.*$'),
                    deny=(
                        r'www\.propublica\.org\/newsletters\/',
                        r'www\.propublica\.org\/about\/',
                        r'www\.propublica\.org\/local-initiatives\/',
                        r'www\.propublica\.org\/jobs\/',
                        r'www\.propublica\.org\/video\/',
                        r'www\.propublica\.org\/impact\/',
                        r'www\.propublica\.org\/contact\/',
                        r'www\.propublica\.org\/feeds\/propublica\/',
                        r'www\.propublica\.org\/tips\/',
                        r'www\.propublica\.org\/steal-our-stories\/',
                        r'give\.propublica\.org\/give\/',
                        r'www\.propublica\.org\/support\/',
                        r'www\.propublica\.org\/code-of-ethics\/',
                        r'www\.propublica\.org\/advertising\/',
                        r'www\.propublica\.org\/legal\/',
                        r'www\.propublica\.org\/leadership\/',
                        r'www\.propublica\.org\/staff\/',
                        r'www\.propublica\.org\/diversity\/',
                        r'www\.propublica\.org\/fellowships\/',
                        r'www\.propublica\.org\/media-center\/',
                        r'www\.propublica\.org\/reports\/',
                        r'www\.propublica\.org\/awards\/',
                        r'www\.propublica\.org\/corrections\/',
                        r'www\.propublica\.org\/getinvolved\/',
                        r'www\.propublica\.org\/events\/',
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

        creation_date = response.xpath('//time[@class="timestamp"]/@datetime').get()
        if not creation_date:
            return
        try:
            creation_date = datetime.fromisoformat(creation_date.split('EDT')[0])
        except:
            creation_date = datetime.fromisoformat(creation_date.split('EST')[0])
            
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[@data-pp-blocktype="copy"]')]
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

        item['news_outlet'] = 'pro_publica'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//meta[@property="author"]/@content').get()
        item['author_person'] = authors.split(',') if authors else list()
        item['author_organization'] = list()
       
        # Extract keywords, if available
        item['news_keywords'] = list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@name="description"]/@content').get().strip()

         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        if response.xpath('//h3[not(@*)] | //h3[@data-pp-blocktype="heading"]'):
            # Extract headlines
            headlines = [h3.xpath('string()').get().strip() for h3 in response.xpath('//h3[not(@*)] | //h3[@data-pp-blocktype="heading"]')]

            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//p[@data-pp-blocktype="copy"] | //h3[not(@*)] | //h3[@data-pp-blocktype="heading"]')]

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
