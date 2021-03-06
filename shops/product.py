# -*- coding: utf-8 -*-

"""
shops.product
~~~~~~~~~~~~~

This module contains the class representing a product.

"""


class Product(object):
    """Class representing a product."""

    def __init__(self, id_, name, price=None, unitary_price=None, unit=None):
        self.id = id_
        self.name = name
        self.price = price
        self.unitary_price = unitary_price
        self.unit = unit

    def __str__(self):
        output = self.id + " - " + self.name

        if self.price:
            output += " >>> " + '{0:.2f} €'.format(self.price)

        if self.unitary_price and self.unit:
            output += ' [{0:.2f} €/{1}]'.format(self.unitary_price, self.unit)

        return output
