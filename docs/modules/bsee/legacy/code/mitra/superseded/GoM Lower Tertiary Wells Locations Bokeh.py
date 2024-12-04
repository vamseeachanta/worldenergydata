import pandas as pd
import csv
import os
import matplotlib.pyplot as plt
import bokeh
from bokeh.io import show,output_file
from bokeh.models import (GMapPlot,GMapOptions, ColumnDataSource,Circle,DataRange1d,PanTool,WheelZoomTool,BoxSelectTool)
plt.style.use("ggplot")
df = pd.read_csv('C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\0119gomwells\\csv files\\alaminos canyas.csv')
x1 = df['Surface Latitude']
##x2 = df['Bottom Latitude']
y1 = df['Surface Longitude']
##y2 = df['Bottom Longitude']
map_options = GMapOptions(lat=25.681137,lng=-89.890137,map_type='terrain',zoom=6)
##api_key = os.environ['API_KEY']
plot = GMapPlot(x_range=DataRange1d(x1),y_range=DataRange1d(y1),
                map_options=map_options)
plot.api_key = "AIzaSyCeSZRBnQv7h-5AEuucJjMzF0tNsR7uHtg"
plot.add_tools(PanTool(), WheelZoomTool(), BoxSelectTool())
source = ColumnDataSource(data=dict(lat = df['Surface Latitude'],
                                    lon = df['Surface Longitude']))
circle = Circle(x='lon',
                y='lat',
                fill_color='red',
                fill_alpha=1.0)
plot.add_glyph(source,circle)
show(plot)

                

