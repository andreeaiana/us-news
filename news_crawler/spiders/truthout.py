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

class TruthoutSpider(BaseSpider):
    """ Spider for Truthout """
    name = 'truthout'
    rotate_user_agent = True
    allowed_domains = ['truthout.org']
    start_urls = ['https://truthout.org']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'truthout\.org\/articles\/\w.*$'),
                    deny=(
                        r'truthout\.org\/articles\/keeley-schenwar-memorial-essay-prize',
                        r'truthout\.org\/about\/',
                        r'truthout\.org\/donate\/',
                        r'truthout\.org\/submission-guidelines\/',
                        r'truthout\.org\/financial-information\/',
                        r'truthout\.org\/privacy-policy\/',
                        r'truthout\.org\/job-openings\/',
                        r'truthout\.org\/contact-us\/',
                        r'truthout\.org\/manage-your-donation\/'
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

        creation_date = response.xpath('//time[@itemprop="datePublished dateCreated"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('T')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(@*) and not(ancestor::div[@class="truth-post-content-after"]) and not(ancestor::div[@class="authorcontent columns"]) and not(ancestor::div[@class="textwidget custom-html-widget"]) and not(ancestor::div[@data-callout-id="modalSubscribe"])] | //ul[not(@*)]/li')]
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

        item['news_outlet'] = 'truthout'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@property="article:modified_time"]/@content').get()
        last_modified = datetime.fromisoformat(last_modified.split('T')[0])
        item['last_modified'] = last_modified.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors_person = response.xpath('//dl[@class="article__authors byline" and not(ancestor::aside[@class="related articles"])]/dd[@itemprop="author"]/span/a[@rel="author"]/text()').getall()
        authors_organization = response.xpath('//dl[@class="article__authors byline" and not(ancestor::aside[@class="related articles"])]/dd[@itemprop="sourceOrganization"]/span/a/text()').getall()
        item['author_person'] = authors_person if authors_person else list()
        item['author_organization'] = authors_organization if authors_organization else list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//article[@itemprop="mainEntity"]/@class').get()
        if news_keywords:
            news_keywords = news_keywords.split(' ')
            news_keywords = [keyword for keyword in news_keywords if 'tag-' in keyword]
            news_keywords = [keyword.split('tag-')[-1] for keyword in news_keywords]
            item['news_keywords'] = news_keywords
        else:
            item['news_keywords'] = list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@name="description"]/@content').get().strip()

         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        if response.xpath('//h2[not(@*)]'):
            # Extract headlines
            headlines = [h2.xpath('string()').get().strip() for h2 in response.xpath('//h2[not(@*)]')]

            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(@*) and not(ancestor::div[@class="truth-post-content-after"]) and not(ancestor::div[@class="authorcontent columns"]) and not(ancestor::div[@class="textwidget custom-html-widget"]) and not(ancestor::div[@data-callout-id="modalSubscribe"])] | //ul[not(@*)]/li | //h2[not(@*)]')]

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
        recommendations = response.xpath('//aside[@class="related articles"]//a[@class="archive-image"]/@href').getall()
        item['recommendations'] = recommendations if recommendations else list()

        item['response_body'] = response.body
        
        yield item
