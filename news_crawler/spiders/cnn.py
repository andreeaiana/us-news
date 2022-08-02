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

class CNNSpider(BaseSpider):
    """ Spider for CNN """
    name = 'cnn'
    rotate_user_agent = True
    allowed_domains = ['edition.cnn.com']
    start_urls = ['https://edition.cnn.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'edition\.cnn\.com\/\w.*$'),
                    deny=(
                        r'edition\.cnn\.com\/sitemap\.html',
                        r'edition\.cnn\.com\/audio',
                        r'edition\.cnn\.com\/videos',
                        r'edition\.cnn\.com\/newsletters',
                        r'edition\.cnn\.com\/terms',
                        r'edition\.cnn\.com\/privacy',
                        r'edition\.cnn\.com\/about',
                        r'edition\.cnn\.com\/msa',
                        r'edition\.cnn\.com\/interactive\/storm-tracker',
                        r'edition\.cnn\.com\/interactive\/\d+\/weather\/\w.*',
                        r'edition\.cnn\.com\/specials\/photos',
                        r'edition\.cnn\.com\/specials\/profiles',
                        r'edition\.cnn\.com\/specials\/more\/cnn-leadership'
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

        creation_date = response.xpath('//meta[@property="og:pubdate"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('T')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="zn-body__paragraph" and not(descendant::h3)]')]
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

        item['news_outlet'] = 'cnn'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@name="lastmod"]/@content').get()
        last_modified = datetime.fromisoformat(last_modified.split('T')[0])
        item['last_modified'] = last_modified.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//meta[@name="author"]/@content').get()
        if authors:
            authors = authors.split(', CNN')[0]
            authors = authors.split('Written by ')[-1].split(';')[0] if 'Written by ' in authors else authors
            authors = authors.split('Opinion by ')[-1] if 'Opinion by ' in authors else authors
            if ' and ' in authors:
                other_authors, last_author = authors.split(' and ')
                other_authors = other_authors.split(', ')
                authors = other_authors + [last_author]
            else:
                authors = authors.split(', ')
            item['author_person'] = authors 
            item['author_organization'] = list()
        else:
            item['author_person'] = list()
            item['author_organization'] = list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//meta[@name="keywords"]/@content').get()
        item['news_keywords'] = news_keywords.split(' - CNN')[0].split(', ', 1) if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@name="description"]/@content').get().strip()

         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        if response.xpath('//div[@class="zn-body__paragraph"]/h3'):
            # Extract headlines
            headlines = [h3.xpath('string()').get().strip() for h3 in response.xpath('//div[@class="zn-body__paragraph"]/h3')]

            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="zn-body__paragraph" and not(descendant::h3)] | //div[@class="zn-body__paragraph"]/h3')]

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
