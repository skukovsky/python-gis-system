import sys, os, itertools, operator
from collections import OrderedDict
import datetime 

import shapely
from shapely.geometry import asShape as geojson2shapely

import rtree 

from . import loader
from . import saver

def ID_generator():
    i = 0
    while True:
        yield i
        i += 1

class VectorData:
    def __init__(self, filepath=None, type=None, **kwargs):
        self.filepath = filepath
        self.type = type

        if filepath:
            fields, rows, geometries, crs = loader.from_file(filepath, **kwargs)
        else: 
            fileds, row, geometries, crs = [], [], [], "+proj=longlat+ellps=WGS84 + datum=WGS84 +no_defs"
        
        self.fields = fields
        self._id_generator = ID_generator()

        ids_rows_geoms = itertools.izip(self._id_generator, rows, geometries)
        featureobjs = (Feature(self, row, geom, id=id) for id, row, geom in ids_rows_geoms)
        
        self.features = OrderedDict([(feat.id, feat) for feat in featureobjs])
        self.crs = crs
    
    def __len__(self): 
        return len(self.features)
    
    def __iter__(self): 
        for feat in self.features.itervalues():
            yield feat
    
    def __