import os, os.path
from osgeo import ogr
from osgeo import osr
from osgeo import gdal
# selecting source and destination datum and cordination transformation from NAD27 to WGS84
SourceDatum = osr.SpatialReference()
SourceDatum.SetWellKnownGeogCS('NAD27')

DestinationDatum = osr.SpatialReference()
DetinationDatum.SetWellKnownGeogCS('WGS84')

transform = osr.CoordinateTransformation(SourceDatum,DestinationDatum)


ShapeFileData = ogr.Open("D:\\mithra\\New folder (2)\\al_20180301.shp")
Shapelayer = ShapeFileData.GetLayer(0)

for i in range(Shapelayer.GetFeatureCount()):
    feature = Shapelayer.GetFeature(i)
    geometry = feature.GetGeometryRef()
