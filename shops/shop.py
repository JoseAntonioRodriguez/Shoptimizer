# -*- coding: utf-8 -*-

"""
shops.shop
~~~~~~~~~~

This module contains the base class to be extended by classes implementing specific shops.

"""

import abc
import csv
from datetime import datetime


class Shop(object):
    """Base Class for shop crawlers"""

    __metaclass__ = abc.ABCMeta

    def __init__(self, name=None, debug=False, verbose=False, fake=False):
        # Shop's name
        self.name = name
        if not self.name:
            self.name = self.__class__.__name__
        # Debug mode (unused now)
        self.debug = debug
        # Print product information while parsing the product's list
        self.verbose = verbose
        # Product's list is got from a local file, instead of the shop server (Used to speed up debugging)
        self.fake = fake
        self.product_dict = {}

    def log(self, resp):
        """Print resp content"""

        if self.verbose:
            print 'Status Code: ', resp.status_code
            #print '       Body: ', resp.text
            print '    History: ', resp.history
            print '   Last URL: ', resp.url
            print '    Cookies: ', resp.cookies

    @abc.abstractmethod
    def get_product_list_page(self):
        """Abstract method to get the HTML page which has the product list"""
        pass

    @abc.abstractmethod
    def parse_product_list_page(self, html_page):
        """Abstract method to parse the HTML page which has the product list and populate the product_dict"""
        pass

    def gather_products(self):
        """Do the crawling and fill the product list"""

        if not self.fake:
            # Get the product list HTML page from the server
            html_page = self.get_product_list_page()

#            # Dump the page to be used later in fake mode
#            f = open('data/' + self.__class__.__name__ + '_fake_page.html', 'w')
#            f.write(html_page)
#            f.close()
        else:
            # Get the product list HTML page from a previously saved file
            f = open('data/' + self.__class__.__name__ + '_fake_page.html', 'r')
            html_page = f.read()
            f.close()

        self.parse_product_list_page(html_page)

    def add_product(self, product):
        self.product_dict[product.id] = product

        if self.verbose:
            print product

    def get_product(self, product_id):
        return self.product_dict.get(product_id)

    def export_csv(self, filename=None):
        """Export product_dict as a csv file"""

        if not filename:
            filename = 'data/' + self.name + '_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.csv'

        with open(filename, 'wb') as csvfile:
            writer = csv.writer(csvfile)
            for product in self.product_dict.values():
                writer.writerow([product.id, product.name, product.price])
