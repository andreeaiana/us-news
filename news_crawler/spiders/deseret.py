# -*- coding: utf-8 -*-

import os
import sys
import json
from news_crawler.spiders import BaseSpider
from scrapy.spiders import Rule 
from scrapy.linkextractors import LinkExtractor
from datetime import datetime

sys.path.insert(0, os.path.join(os.getcwd(), "..",))
from news_crawler.items import NewsCrawlerItem
from news_crawler.utils import remove_empty_paragraphs

class DeseretSpider(BaseSpider):
    """ Spider for Deseret News """
    name = 'deseret'
    rotate_user_agent = True
    allowed_domains = ['www.deseret.com']
    start_urls = ['https://www.deseret.com']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.deseret\.com\/\w.*$'),
                    deny=(
                        r'www\.deseret\.com\/pages\/legal-notices',
                        r'www\.deseret\.com\/pages\/about-us',
                        r'www\.deseret\.com\/pages\/tv-listings',
                        r'www\.deseret\.com\/pages\/editorial-team',
                        r'www\.deseret\.com\/pages\/contact-us',
                        r'www\.deseret\.com\/pages\/advertise-with-the-deseret-news',
                        r'www\.deseret\.com\/contact\/technical-support',
                        r'www\.deseret\.com\/legal\/donotsell',
                        r'www\.deseret\.com\/legal\/terms-of-use',
                        r'www\.deseret\.com\/legal\/privacy-notice',
                        r'www\.deseret\.com\/legal\/cookie-policy'
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
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="RichTextArticleBody RichTextBody"]/p | //div[@class="RichTextArticleBody RichTextBody"]/ul/li')]
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

        item['news_outlet'] = 'deseret_news'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@property="article:modified_time"]/@content').get()
        last_modified = datetime.fromisoformat(last_modified.split('T')[0])
        item['last_modified'] = last_modified.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//meta[@name="parsely-author"]/@content').getall()
        item['author_person'] = [author for author in authors if author != "Readers' Forum"] if authors else list()
        item['author_organization'] = ["Readers' Forum"] if "Readers' Forum" in authors and authors else list()
       
        # Extract keywords, if available
        data_json = response.xpath('//script[@type="application/ld+json"]/text()').get()
        if data_json:
            data = json.loads(data_json)
            news_keywords = data['keywords']
        else:
            news_keywords = list()
        item['news_keywords'] = news_keywords

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@name="description"]/@content').get().strip()

         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        if response.xpath('//h3'):
            # Extract headlines
            headlines = [h3.xpath('string()').get().strip() for h3 in response.xpath('//h3')]

            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="RichTextArticleBody RichTextBody"]/p | //div[@class="RichTextArticleBody RichTextBody"]/ul/li | //h3')]

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
        recommendations = response.xpath('//ul[@class="RelatedList-items"]/li/a/@href').getall()
        item['recommendations'] = list(set(recommendations))[:5] if recommendations else list()

        item['response_body'] = response.body
        
        yield item
