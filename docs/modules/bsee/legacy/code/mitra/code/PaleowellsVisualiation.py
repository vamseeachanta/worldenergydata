import geopandas as gpd
import folium
import pandas as pd
import folium
import openpyxl
from folium.plugins import MarkerCluster
paleogeneData =pd.read_excel("C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\calculations\\Paleogenewells.xlsx",sheet_name ='Lowertertiarywells')
shapeFile = gpd.read_file("C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\data\\al_20180501.shp")

map1 = folium.Map(location=[25.681137,-89.890137],
               tiles='Mapbox Bright', zoom_start=5)


for i in range(0,len(paleogeneData)):
    feature_group = folium.FeatureGroup(name='quiver')
    def color_producer(xyz):
        if xyz == "PA": return "red" 
        elif xyz == "COM": return "blue"
        elif xyz == "ST": return "pink"
        elif xyz == "TA": return "darkred"

    
        
    def abbrevation(x):
        if x == "PA": return "Permanetely Abandoned"
        elif x == "COM": return "Completed"
        elif x == "ST": return "Side Tracked"
        elif x == "TA": return "Temporarily Abandoned"
        
    folium.Marker([paleogeneData.iloc[i]["Latitude"],paleogeneData.iloc[i]['Longitude']],
              popup=paleogeneData.iloc[i].apply(str)["WellAPI"]+ '<br>' 
                  +paleogeneData.iloc[i]["CompanyName"]+ '<br>' 
                  +(abbrevation(paleogeneData.iloc[i]["WellStatus"]))+ "<br>" 
                  +paleogeneData.iloc[i].apply(str)["BlockName"]+ "<br>" 
                  +paleogeneData.iloc[i].apply(str)["BlockNumber"]+ "<br>" +paleogeneData.iloc[i]["LeaseNumber"],
                  icon=folium.Icon(color=color_producer(paleogeneData.iloc[i]["WellStatus"]))).add_to(map1)
    map1.add_child(feature_group)
        
        
folium.GeoJson(shapeFile).add_to(map1)
map1.save('C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\calculations\\actleaseshp.html')  
