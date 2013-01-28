# -*- coding: utf-8 -*-

"""
shops.eroski
~~~~~~~~~~~~

This module contains the class implementing the crawler for Eroski.

"""

import re
import requests
import lxml.html

from shop import Shop
from product import Product


class Eroski(Shop):
    """Eroski crawler"""

    def __init__(self, username, password, list_name, debug=False, verbose=False, fake=False):
        Shop.__init__(self, debug=debug, verbose=verbose, fake=fake)
        # Credentials to access to the shop
        self.username = username
        self.password = password
        # Name of the product's list to be parsed as named in the server
        self.list_name = list_name

    def get_unitary_price(self, price, name, category):
        """Try to get the units, weight, capacity, etc. from the product name and calculate the unitary price"""

        result = re.search(r'.* ((?:\d+[x+])?\d+(?:,\d+)?) (g|litro|cl|ml|rollos|unid\.|kg|dosis)', name)
        try:
            amount, unit = result.group(1, 2)
        except:
            return 0.0, 'N/A'

        amount = amount.replace(',', '.')
        if 'x' in amount:
            amount = amount.partition('x')
            amount = float(amount[0]) * float(amount[2])
        elif '+' in amount:
            amount = amount.partition('+')
            amount = float(amount[0]) + float(amount[2])
        else:
            amount = float(amount)

        if unit == 'g':
            unitary_price, unit = price / amount * 1000.0, 'kg'
        elif unit == 'kg':
            unitary_price, unit = price / amount, 'kg'
        elif unit == 'litro':
            unitary_price, unit = price / amount, 'l'
        elif unit == 'cl':
            unitary_price, unit = price / amount * 100.0, 'l'
        elif unit == 'ml':
            if category == 'Perfumería':
                unitary_price, unit = price / (amount / 100.0), '100 ml'
            else:
                unitary_price, unit = price / amount * 1000.0, 'l'
        elif unit == 'rollos' or unit == 'unid.':
            unitary_price, unit = price / amount, 'ud'
        elif unit == 'dosis':
            unitary_price, unit = price / amount, 'dosis'
        else:
            raise ValueError('Non recognized measurement unit')

        return round(round(unitary_price, 4), 2), unit  # TODO: Warning!!! floats are not precise

    def get_product_list_page(self):
        """Get the HTML page which has the product list"""

        session = requests.session()

        resp = session.get('http://www.compraonline.grupoeroski.com/ecoventa/index.jsp', allow_redirects=False)
        self.log(resp)

        form_params = {'from': 'index',
                       'tipo': 'P',
                       'CajaLaboral': 'null',
                       'shlogid': self.username,
                       'shlpswd': self.password}
        resp = session.post('https://www.compraonline.grupoeroski.com/ecoventa/actions/accesoUsuarioRegistrado.do',
                            data=form_params)
        self.log(resp)
        #resp = session.get('http://www.compraonline.grupoeroski.com/ecoventa/actions/mostrarDireccionesEnvio.do')

        form_params = {'ultimasCompras': 'NO',
                       'sarfnbr': '3251371'}
        resp = session.post('https://www.compraonline.grupoeroski.com/ecoventa/actions/seleccionarDireccionEnvio.do',
                            data=form_params, allow_redirects=False)
        self.log(resp)

        resp = session.get('http://www.compraonline.grupoeroski.com/ecoventa/actions/mostrarListaHabitualUsuario.do')
        self.log(resp)

        html_tree = lxml.html.fromstring(resp.text, parser=lxml.html.HTMLParser(encoding='utf-8'))
        try:
            url = html_tree.xpath("//div[@id='divListas']//"
                                  "a[text()='- " + self.list_name + "']")[0].attrib['href']
        except:
            raise ValueError('List name "' + self.list_name + '" not found')

        resp = session.get('http://www.compraonline.grupoeroski.com' + url.strip())
        self.log(resp)

        return resp.text

    def parse_product_list_page(self, html_page):
        """Parse the HTML page which has the product list and populate the product_dict"""

        html_tree = lxml.html.fromstring(html_page, parser=lxml.html.HTMLParser(encoding='utf-8'))

        product_list = html_tree.xpath("//table[@id='conte']/form/tr[starts-with(@id, 'prod_') or "
                                       "starts-with(@id, 'categ_')]")
        #print len(product_list)

        for product_item in product_list:
            # Get product category
            product_id = product_item.attrib['id']
            if product_id.startswith('categ_'):
                if not product_id.endswith('_2'):
                    product_category = product_item.xpath("./td/table/tr/td[2]/p")[0].text.strip(' >')
                    #print product_category
                continue

            base_xpath = "./td/table/tr/td/table/tr/td[3]/table"
            # Check whether the product is available
            if len(product_item.xpath(base_xpath + "/tr[3]/td/table/tr/td[@class='sub_menu_11']/a/"
                                                   "strong[text()='Busca Sustituto']")) > 0:
                continue

            product_id = product_id.partition('_')[2]
            product_name = product_item.xpath(base_xpath + "/tr/td/table/tr/td[@class='menu_sup11']")[0].\
                                              text_content().strip()
            product_price = float(product_item.xpath(base_xpath +
                                                     "/tr[3]/td/table/tr/td[@class='menu_12_rojo_sin']/strong")[0].\
                                                     text.partition(' ')[0].replace(',', '.'))

            # The following are fixings to normalize shop "bugs"
            if product_id == '900782_2058535':
                product_name = product_name.replace('3x80', '3x60')

            product_unitary_price, product_unit = self.get_unitary_price(product_price, product_name, product_category)

            Shop.add_product(self,
                             Product(product_id, product_name, product_price, product_unitary_price, product_unit))
