#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
#
# Copyright (C) 2015-2020 Daniel Rodriguez
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import backtrader as bt


class GridLine(bt.Indicator):
    '''
    GridLine
    '''
    lines = ('priceline',)
    params = (('price', 0),)
    plotinfo = dict(subplot=False)
    plotlines = dict(
        priceline=dict(_samecolor=True),
    )
    def next(self):
        if (self.p.price != self.lines.priceline[-1] and self.p.price > 0):
            self.lines.priceline[0] = self.p.price
        else : self.lines.priceline[0] = self.lines.priceline[-1]
