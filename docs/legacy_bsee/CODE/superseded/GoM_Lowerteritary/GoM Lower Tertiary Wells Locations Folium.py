import pandas as pd
import folium
from IPython.display import HTML, display
import csv
from folium.plugins import MarkerCluster
import io
URL_LIST = ["C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\0119gomwells\\csv files\\alaminos canyas.csv",
            "C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\0119gomwells\\csv files\\walker ridge.csv",
            "C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\0119gomwells\\csv files\\gb.csv",
            "C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\0119gomwells\\csv files\\gcr.csv",
            "C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\0119gomwells\\csv files\\pi.csv",
            "C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\0119gomwells\\csv files\\se.csv"]
dfs = [pd.read_csv(url) for url in URL_LIST]
df = pd.concat(dfs)
list = [600,903,857,818,859,739,812,813,814,
        900,901,206,469,678,759,544,969,51,205,249,
        250,425,426,470,959,785,736,292,872,102,525,39,807]
xx = []
x2 = []
x3 = []
x4 = []
for row in df:
    if  row =='Bottom Block':
        for j in list:
            x =  df[df[row] == j][row]
            x1 = df[df[row] == j]["Company Name"]
            y =  df[df[row] == j]["Surface Latitude"]
            y1 = df[df[row] == j]['Surface Longitude']
            xx.append(x)
            x2.append(x1)
            x3.append(y)
            x4.append(y1)
##multiple list in a list to make using concat method            
            x5 = pd.concat(x2)
            x6 = pd.concat(x3)
            x7 = pd.concat(x4)

##creating new csv file with output data and DataFrame          
list2 = [["Company Name"]+["Surface Latitude"]+['Surface Longitude']]
with open('C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\0119gomwells\\csv files\\output.csv',"a") as output:
    writer = csv.writer(output,lineterminator = '\n')
    writer.writerows(list2)
    writer.writerows([])
dj = pd.read_csv('C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\0119gomwells\\csv files\\output.csv')
dj1 = pd.DataFrame({"Company Name":(x5),
                   "Surface Latitude":(x6),
                   'Surface Longitude':(x7)})


##creating geograpic map with folium
map1 = folium.Map(location=[25.681137,-89.890137],
               tiles='Mapbox Bright', zoom_start=5)

for i in range(0,len(dj1)):
    feature_group = folium.FeatureGroup(name='quiver')
##marking points using folium marker
    folium.Marker([dj1.iloc[i]["Surface Latitude"],dj1.iloc[i]['Surface Longitude']], popup=dj1.iloc[i]["Company Name"],icon=folium.Icon(color='red',icon='info-sign')).add_to(map1)
    map1.add_child(feature_group)

map1.save('#394_folium_gom wells1.html')
##markercluster for overlapping data 
map2 = folium.Map(location=[25.681137,-89.890137],
               tiles='Stamen Terrain', zoom_start=6)    
marker_cluster = MarkerCluster().add_to(map2)
for i in range(0, len(dj1)):
    folium.Marker([dj1.iloc[i]["Surface Latitude"],dj1.iloc[i]['Surface Longitude']], popup=dj1.iloc[i]["Company Name"],icon=folium.Icon(color='red',icon='info-sign')).add_to(marker_cluster)

map2.save('#395_folium_gom wells1.html')


    



    

          
            
        
