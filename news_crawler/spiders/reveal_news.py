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

class RevealNewsSpider(BaseSpider):
    """ Spider for The Center for Investigative Reporting (CIR) """
    name = 'reveal_news'
    rotate_user_agent = True
    allowed_domains = ['revealnews.org']
    start_urls = ['https://revealnews.org']

    # Exclude irelevant pages
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'revealnews\.org\/article\/\w.*$'),
                    deny=(
                        r'revealnews\.org\/podcast\/',
                        r'revealnews\.org\/watch-tv-films\/',
                        r'revealnews\.org\/about-us\/',
                        r'revealnews\.org\/pitching-reveal\/',
                        r'revealnews\.org\/republishing-guidelines\/',
                        r'revealnews\.org\/terms-of-use\/',
                        r'revealnews\.org\/privacy-policy\/',
                        r'revealnews\.org\/corrections\/',
                        r'revealnews\.org\/where-to-hear-reveal\/',
                        r'revealnews\.org\/feed\/',
                        r'revealnews\.org\/newsletter\/',
                        r'revealnews\.org\/press-releases\/',
                        r'revealnews\.org\/topic\/inside-the-newsroom\/'
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
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(@class) and not(ancestor::div[@class="wrapper"]) and not(ancestor::div[@class="author-bio"] and not(ancestor::div[@class="entry-wrapper"])) and not(descendant::aside/amp-analytics/script[@type="application/json"])] | //p[@data-ce-tag="paragraph" and contains(@class, "stk-reset wp-exclude-emoji")] | //p[@data-ce-tag="paragraph" and @class="stk-reset stk-theme_41108__mb_15 wp-exclude-emoji"]')]
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

        item['news_outlet'] = 'reveal_news'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@property="article:modified_time"]/@content').get()
        last_modified = datetime.fromisoformat(last_modified.split('T')[0])
        item['last_modified'] = last_modified.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//span[@class="author vcard"]/a/text()').getall()
        item['author_person'] = authors if authors else list()
        item['author_organization'] = list()
       
        # Extract keywords, if available
        news_keywords = response.xpath('//footer[@class="entry-footer"]/span[@class="tags-links"]/a[@rel="tag"]/text()').getall()
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
            text = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(@class) and not(ancestor::div[@class="wrapper"]) and not(ancestor::div[@class="author-bio"] and not(ancestor::div[@class="entry-wrapper"])) and not(descendant::aside/amp-analytics/script[@type="application/json"])] | //p[@data-ce-tag="paragraph" and contains(@class, "stk-reset wp-exclude-emoji")] | //p[@data-ce-tag="paragraph" and @class="stk-reset stk-theme_41108__mb_15 wp-exclude-emoji"] | //h3[not(@*)]')]

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
