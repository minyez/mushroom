#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""simple scrapper"""
import requests

try:
    from bs4 import BeautifulSoup as BS
except ImportError:
    BS = None

from mushroom.core.ioutils import raise_no_module


class SMPage:
    """object to analyze SpringerMaterialPage"""

    def __init__(self, url):
        self.url = url
        pass

    def analyze(self):
        """analyse all searched items"""
        raise NotImplementedError


class SMSearch:
    """a simple scrapper to search SpringerMaterial data
    Args:
        chemical (str)
        mode (str)
        only_crystal (bool) : only crystallgraphic structure pages are extracted
        pages (int) : the maximum number of search pages to scrap
        interval (int) : the interval for scrapping individual material page
    """

    def __init__(self, chemical, mode='focus', only_crystal=True, pages=1, interval=0):
        urls = {
            'focus': 'https://materials.springer.com/search?searchTerm=',
            'text': 'https://materials.springer.com/textsearch?searchTerm=',
        }
        self._url = urls.get(mode) + chemical
        self.chemical = chemical
        self.only_crystal = only_crystal
        self.interval = interval
        self.results = []
        self._search(pages=pages)

    def search(self, pages=1):
        """searching the SpringMaterial

        Args:
            pages (int) : the maximum number of pages to search
        """
        self.results = []
        self._search(pages=pages)

    def _search(self, pages=1):
        if not self.results:
            for page in range(pages):
                try:
                    r = requests.get(self._url + "&pageNumber=" + str(page))
                    r.raise_for_status()
                    r.encoding = r.apparent_encoding
                    self.extract_items_from_html(r.text)
                except requests.HTTPError:
                    print("warning: failed to get search results on page ", page)

    def _extract_items_from_html(self, html):
        """obtain all item on a search page

        Basically, the attribute required to get a material page is href.
        while `data-track-label` and `database` can provide a quick
        glimse of what the page will probably be concerned with.

        Args:
            html (str) : the html string of search page
        """
        raise_no_module(BS, "BeautifulSoup", "processing html in " + __name__)
        soup = BS(html, 'html.parser')
        for a in soup.find_all('a'):
            c = a.attrs.get('class', [])
            if 'search_result' in c:
                s = [a.attrs['data-track-label'], a.attrs['database'], a.attrs['href'], a.string]
                if (not self.only_crystal or s[2].startswith('/isp/crystallographic/')):
                    self.results.append(s)

