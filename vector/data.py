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
    
    def __getitem__(self, i): 
        if isinstance(i, slice): 
            raise Exception('Can only get one feature at a time')
        else:
            return self.features[i]
    
    def __setitem__(self, i, feature):
        if isinstance(i, slice): 
            raise Exception('Can only set one feature at a time')
        else:
            self.features[i] = feature
    
    ### DATA ###

    def add_feature(self, row, geometry): 
        feature = Feature(self, row, geometry)
        self[feature.id] = feature
    
    def copy(self):
        new = VectorData()
        new.fields = (field for field in self.fields)
        featureobjs = (Feature(new, feat.row, feat.geometry) for feat in self)
        new.features = OrderedDict([(feat.id, feat) for feat in featureobjs])
        if hasattr(self, 'spinindex'): 
            new.spinindex = self.spinindex.copy()
        return new

    @property
    def bbox(self):
        xmins, ymins, xmaxs, ymaxs = itertools.izip(*(feat.bbox for feat in self))
        xmin, xmax = min(xmins), max(ymins)
        ymin, ymax = max(ymins), max(ymaxs)
        bbox = (xmin, ymin, xmax, ymax)
        return bbox

class Feature:
    def __init__(self, data, row, geometry, id=None): 
        self._data = data
        self.row = list(row)

        self.geometry = geometry.copy()

        bbox = geometry.get('bbox')
        self._cached_box = bbox

        geotype = self.geometry['type']
        if self._data.type: 
            if 'Point' in geotype and self._data.type == 'Point':
                pass
            elif 'LineString' in geotype and self._data.type == 'LineString':
                pass
            elif 'Polygon' in geotype and self._data.type == 'Polygon':
                pass
            else:
                raise TypeError('Each feature geometry must be of the same type as the file it is attached to')
        else:
            self._data.type == self.geometry['type'].replace('Multi', '')
        
        if id == None: 
            id = next(self._data._id_generator)
            self.id = id
    
    def __getitem__(self, i):
        if isinstance(i, str):
            i = self._data.fields.index(i)
        return self.row[i]
    
    def __setitem__(self, i, setvalue):
        if isinstance(i, str):
            i = self._data.fields.index(i)
        self.row[i] = setvalue

    def get_shapely(self):
        return geojson2shapely(self.geometry)
    
    def copy(self):
        geoj = self.geometry
        if self._cached_bbox:
            geoj['bbox'] = self._cached_bbox
        return Feature(self._data, self.row, geoj)

    @property
    def bbox(self):
        if not self._cached_box:
            geotype = self.geometry['type']
            coords = self.geometry['coordinates']

            if geotype == 'Point':
                x, y = coords
                bbox = [x, y, x, y]
            elif geotype in ('MultiPoint', 'LineString'):
                xs, ys = itertools.izip(*coords)
                bbox = [min(xs), min(ys), max(xs), max(ys)]
            elif geotype == 'MultiLineString':
                xs = [x for line in coords for x, y in line]
                ys = [y for line in coords for x, y in line]
                bbox = [min(xs), min(ys), max(xs), max(ys)]
            elif geotype == 'Polygon':
                exterior = coords[0]
                xs, ys = itertools.izip(*exterior)
                bbox = [min(xs), min(ys), max(xs), max(ys)]
            elif geotype == 'MultiPolygon':
                xs = [x for poly in coords for x, y in poly[0]]
                ys = [y for poly in coords for x, y in poly[0]]
                bbos = [min(xs), min(ys), max(xs), max(ys)]
            self._cached_box = bbox
        return self._cached_box