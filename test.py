#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Yuki Furuta <furushchev@jsk.imi.i.u-tokyo.ac.jp>

class DotDict(dict):
    def __getattr__(self, attr):
        o = self.get(attr)
        if isinstance(o, dict):
            return DotDict(o)
        else: return o
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

class DDict(dict):
    def getByDot(self, attr):
        val = self
        try:
            for a in  attr.split("."):
                val = val.get(a)
            return val
        except: return "N/A"
