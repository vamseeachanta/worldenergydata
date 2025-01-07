import geopandas as gpd
import numpy as np
from shapely.geometry import Point
import pandas as pd

def dms_to_dec(d):
    sign = np.sign(d)
    return d + sign 

df = pd.read_excel("C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\Parameters_MK\\gomwells.xlsx",sheetname ='Lowertertiarywells')
points = df.apply(lambda row: Point(dms_to_dec(*row[['Longitude']]), 
                                    dms_to_dec(*row[['Latitude']])),
                  axis=1)
gdf_nad83 = gpd.GeoDataFrame(df, geometry=points, crs={'init': 'EPSG:4267'})
wgs84 = gdf_nad83.to_crs({'init': "EPSG:4326"})
print(wgs84)
