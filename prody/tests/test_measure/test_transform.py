#!/usr/bin/python
# -*- coding: utf-8 -*-
# ProDy: A Python Package for Protein Dynamics Analysis
# 
# Copyright (C) 2010-2012 Ahmet Bakan
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>

"""This module contains unit tests for :mod:`prody.measure.transform` module.
"""

__author__ = 'Ahmet Bakan'
__copyright__ = 'Copyright (C) 2010-2012 Ahmet Bakan'

import unittest
from numpy import zeros, ones
from numpy.testing import assert_equal

from prody.tests.test_datafiles import parseDatafile

from prody.measure import moveAtoms


class TestMoveAtoms(unittest.TestCase):
    
    
    def setUp(self):
        
        self.ag = parseDatafile('1ubi')
    
    def testToArgument(self):
        
        atoms = self.ag.ca
        
        coords = self.ag.getCoords()
        center = atoms._getCoords().mean(0)
        moveAtoms(atoms, to=zeros(3), ag=True)
        assert_equal(self.ag._getCoords(), coords - center)
        
    def testByArgument(self):
        
        atoms = self.ag
        offset = ones(3) * 10.
        coords = atoms.getCoords()
        moveAtoms(atoms, by=offset)
        assert_equal(atoms._getCoords(), coords + offset)
        
