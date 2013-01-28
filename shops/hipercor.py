# -*- coding: utf-8 -*-

"""
shops.hipercor
~~~~~~~~~~~~~~

This module contains the class implementing the crawler for Hipercor.

"""

import re
import requests
import lxml.html

from shop import Shop
from product import Product


class Hipercor(Shop):
    """Hipercor crawler"""

    def __init__(self, username, password, list_name, debug=False, verbose=False, fake=False):
        Shop.__init__(self, debug=debug, verbose=verbose, fake=fake)
        # Credentials to access to the shop
        self.username = username
        self.password = password
        # Name of the product's list to be parsed as named in the server
        self.list_name = list_name

    def normalize_unitary_price(self, unitary_price, unit):
        """Change units used by the sop to a common (normalized) set of units to be used internally"""

        if unit == 'Kilo':
            return unitary_price, 'kg'
        elif unit == 'Litro':
            return unitary_price, 'l'
        elif unit == '100 ml.':
            return unitary_price, '100 ml'
        elif unit == 'Unidad':
            return unitary_price, 'ud'
        elif unit == 'Docena':
            return round(round(unitary_price / 12, 4), 2), 'ud'  # TODO: Warning!!! floats are not precise
        elif unit == 'Dosis':
            return unitary_price, 'dosis'
        else:
            raise ValueError('Non recognized measurement unit')

    def get_unitary_price(self, price, name):
        """Try to get the units, weight, capacity, etc. from the product name and calculate the unitary price"""

        result = re.search(r'.* (\d+) (unidades|l)', name)
        amount, unit = result.group(1, 2)
        amount = float(amount)

        if unit == 'unidades':
            unitary_price, unit = price / amount, 'ud'
        elif unit == 'l':
            unitary_price, unit = price / amount, 'l'
        else:
            raise ValueError('Non recognized measurement unit')

        return round(round(unitary_price, 4), 2), unit  # TODO: Warning!!! floats are not precise

    def get_product_list_page(self):
        """Get the HTML page which has the product list"""

        session = requests.session()

        #resp = session.get('http://www.hipercor.es/')
        resp = session.get('http://www.hipercor.es/hiper')
        self.log(resp)

        resp = session.get('https://www.hipercor.es/hipercor/sm2/login/login.jsp')
        self.log(resp)

        html_tree = lxml.html.fromstring(resp.text, parser=lxml.html.HTMLParser(encoding='utf-8'))
        dynSessConf = html_tree.xpath("//input[@name='_dynSessConf']")[0].attrib['value']

        # Petición para forzar la cookie PD-H-SESSION-ID
        resp = session.get('https://www.hipercor.es/profile2/profile/auth/TAM/AutenticaUsuario?'
                           'migrar=1&datincom=0&urltam=https://www.hipercor.es/hipercor/sm2/login/login.jsp')
        self.log(resp)

        form_params = {'_dyncharset': 'iso-8859-15',
                       '_dynSessConf': dynSessConf,
                       'pag_regreso': 'https://www.hipercor.es/hipercor/sm2/login/login.jsp',
                       'pag_error': 'https://www.hipercor.es/hipercor/sm2/login/login.jsp?_errorValidationTAM=true',
                       'grupo': 'ECI',
                       'Username': self.username,
                       'password': self.password,
                       'group1': 'homeDelivery'}
        resp = session.post('https://www.hipercor.es/profile2/profile/LoginServlet?'
                            '_DARGS=/sm2/common/public/homeHipercorContainer.jsp', data=form_params)
        self.log(resp)

        html_tree = lxml.html.fromstring(resp.text, parser=lxml.html.HTMLParser(encoding='utf-8'))
        username = html_tree.xpath("//input[@name='username']")[0].attrib['value']
        password = html_tree.xpath("//input[@name='password']")[0].attrib['value']
        form_params = {'login-form-type': 'pwd',
                       'username': username,
                       'password': password}
        resp = session.post('https://www.hipercor.es/pkmslogin.form?'
                            'pag_error=https://www.hipercor.es/hipercor/sm2/login/login.jsp?_errorValidationTAM=true',
                            data=form_params)
        self.log(resp)
        #resp = session.get('https://www.hipercor.es/profile2/profile/auth/TAM/AutenticaUsuario?'
        #                   'migrar=1&datincom=0&urltam=https://www.hipercor.es/hipercor/sm2/login/login.jsp',
        #                   allow_redirects=False)
        #resp = session.get(resp.headers['Location'], allow_redirects = False)

        html_tree = lxml.html.fromstring(resp.text, parser=lxml.html.HTMLParser(encoding='utf-8'))
        dynSessConf = html_tree.xpath("//input[@name='_dynSessConf']")[0].attrib['value']
        form_params = {'_dyncharset': 'iso-8859-15',
                       '_dynSessConf': dynSessConf,
                       'group1': 'homeDelivery',
                       '_D:group1': ' ',
                       '_D:group1': ' ',
                       '_D:group1': ' ',
                       'Aceptar': 'Aceptar',
                       '_D:Aceptar': ' ',
                       '_DARGS': '/sm2/login/LoginOptionsLoggedUser.jsp.frmlogin'}
        resp = session.post('https://www.hipercor.es/hipercor/sm2/login/login.jsp?'
                            '_DARGS=/sm2/login/LoginOptionsLoggedUser.jsp.frmlogin', data=form_params)
        self.log(resp)
        #resp = session.get(resp.headers['Location'], allow_redirects = False)
        #resp = session.get(resp.headers['Location'], allow_redirects = False)
        #resp = session.get(resp.headers['Location'], allow_redirects = False)

        resp = session.get('http://www.hipercor.es/hipercor/sm2/wishlist/wishListView.jsp')
        self.log(resp)

        html_tree = lxml.html.fromstring(resp.text, parser=lxml.html.HTMLParser(encoding='utf-8'))
        try:
            url = html_tree.xpath("//div[@id='contenedor_popup_desplegable_mislistas']//"
                                  "a[span[text()='" + self.list_name + "']]")[0].attrib['href']
        except:
            raise ValueError('List name "' + self.list_name + '" not found')

        resp = session.get('http://www.hipercor.es/' + url)
        self.log(resp)

        return resp.text

    def parse_product_list_page(self, html_page):
        """Parse the HTML page which has the product list and populate the product_dict"""

        html_tree = lxml.html.fromstring(html_page, parser=lxml.html.HTMLParser(encoding='utf-8'))

        product_list = html_tree.xpath("//table[@id='shopping-cart-table']/tbody/tr[not(@class)]")
        #print len(product_list)

        for product_item in product_list:
            # Check whether the product is available
            if len(product_item.xpath("./td[3]/span[text()='Producto no disponible']")) > 0:
                continue

            product_id = product_item.xpath(".//div[@class='cart_product_img']//img/@src")[0].split('/')
            product_id = product_id[len(product_id) - 2]

            product_name = product_item.xpath(".//div[@class='cart_product_txt']/h3/a/span")[0].text
            product_name = product_name.encode('utf-8')

            product_price = float(product_item.xpath(".//p[@class='ahora']/span")[0].text.strip().\
                                  partition(' ')[0].replace(',', '.'))

            product_unitary_price = product_item.xpath(".//div[contains(concat(' ', normalize-space(@class), ' '), "
                                                       "' precio_kg ')]")
            if len(product_unitary_price) > 0:
                product_unitary_price = product_unitary_price[0].text.strip(' ()').partition(' / ')
                product_unit = product_unitary_price[2]
                product_unitary_price = float(product_unitary_price[0].partition(' ')[0].replace(',', '.'))

                # The following are fixings to normalize shop "bugs"
                if product_id == '0201030800187':
                    product_unitary_price *= 2

                product_unitary_price, product_unit = self.normalize_unitary_price(product_unitary_price, product_unit)
            else:
                product_unitary_price, product_unit = self.get_unitary_price(product_price, product_name)

            Shop.add_product(self,
                             Product(product_id, product_name, product_price, product_unitary_price, product_unit))
