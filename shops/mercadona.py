# -*- coding: utf-8 -*-

'''
Created on 15/07/2012

@author: jarf
'''

import re
import requests
import lxml.html

from shop import Shop, Product


class Mercadona(Shop):
    '''
    Mercadona crawler
    '''

    def __init__(self, username, password, id_lista, debug=False, verbose=False, fake=False):
        '''
        Constructor
        '''

        Shop.__init__(self, debug, verbose, fake)
        self.username = username
        self.password = password
        self.id_lista = id_lista

    def normalize_unitary_price(self, unitary_price, unit):
        if unit == '1 KILO':
            return unitary_price, 'kg'
        elif unit == '1 LITRO':
            return unitary_price, 'l'
        elif unit == '100 CC':
            return unitary_price, '100 ml'
        elif unit == '1 UNIDAD':
            return unitary_price, 'ud'
        elif unit == '12 UNIDADes':
            return round(round(unitary_price / 12, 4), 2), 'ud'  # TODO: Warning!!! floats are not precise
        elif unit == '1 LAVADO':
            return unitary_price, 'dosis'
        else:
            raise ValueError('Non recognized measurement unit') 

    def get_unitary_price(self, price, name):
        '''
        Try to get the units, weight, capacity, etc. from the product name and calculate the unitary price
        '''

        result = re.search(r'.* (\d+) (l|cc)', name)
        amount, unit = result.group(1, 2)
        amount = float(amount)

        if unit == 'l':
            unitary_price, unit = price / amount, 'l'
        elif unit == 'cc':
            unitary_price, unit = price / (amount / 100.0), '100 ml'
        else:
            raise ValueError('Non recognized measurement unit')

        return round(round(unitary_price, 4), 2), unit

    def get_product_list_page(self):
        '''
        Get the HTML page which has the product list
        '''

        session = requests.session()

        resp = session.get('https://www.mercadona.es/ns/entrada.php?js=-1')
        self.log(resp)

        form_params = {'AyudaPassword': '',
                       'EntradaUsername': '1',
                       'ImgEntradaAut': 'ENTRAR',
                       'Localidad': '',
                       'Pais': '34',
                       'Provincia': '',
                       'TiendaVisita': '1',
                       'form_origen': 'principal',
                       'pag_origen': 'entrada.php',
                       'password': self.password,
                       'username': self.username}
        resp = session.post('https://www.mercadona.es/ns/entrada.php', data=form_params)
        self.log(resp)

        resp = session.get('https://www.mercadona.es/sfprincipal.php?page=sflista&id_padre=&id_seccion=&id_lista=' +
                           self.id_lista + '&ind=0')  # 12840115
        self.log(resp)

        return resp.text

    def parse_product_list_page(self, html_page):
        '''
        Parse the HTML page which has the product list and populate the product_dict
        '''

        html_tree = lxml.html.fromstring(html_page, parser=lxml.html.HTMLParser(encoding='utf-8'))

        product_list = html_tree.xpath("//table[@class='tablaproductos']/tbody/tr")
        #print len(product_list)

        for product_item in product_list:
            # Check whether the product is available
            if len(product_item.xpath("./td[1]/img[@alt='PRODUCTOS NO DISPONIBLES']")) > 0:
                continue

            product_id = product_item.xpath("./td[4]/input/@value")[0].partition(';')[0]

            product_name = product_item.xpath("./td[1]//label")[0].text.replace(' ***LE RECOMENDAMOS***', '')

            product_price = float(product_item.xpath("./td[2]/span")[0].text.partition(' ')[0].replace(',', '.'))

            product_unitary_price = product_item.xpath("./td[2]/span[contains("
                                                       "concat(' ', normalize-space(@class), ' '), ' precio_ud ')]")
            if len(product_unitary_price) > 0:
                product_unitary_price = product_unitary_price[0].text.partition(': ')
                product_unit = product_unitary_price[0]
                product_unitary_price = float(product_unitary_price[2].partition(' ')[0].replace(',', '.'))

                # The following are fixings to normalize shop "bugs"
                if product_id == '43401':
                    product_unitary_price = product_price
                    product_unit = '1 UNIDAD'
                elif product_id == '40805':
                    amount = re.search(r'(\d+) LAVADOS', product_name).group(1)
                    product_unitary_price = round(round(product_price / float(amount), 4), 2)
                    product_unit = '1 LAVADO'

                product_unitary_price, product_unit = self.normalize_unitary_price(product_unitary_price, product_unit)
            else:
                product_unitary_price, product_unit = self.get_unitary_price(product_price, product_name)

            Shop.add_product(self,
                             Product(product_id, product_name, product_price, product_unitary_price, product_unit))
