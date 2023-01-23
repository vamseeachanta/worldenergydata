import folium
import pandas as pd
from IPython.display import HTML, display

URL_LIST = ['C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\0119gomwells\\csv files\\oxy1.csv',
            'C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\0119gomwells\\csv files\\oxy2.csv',
            'C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\0119gomwells\\csv files\\oxy3.csv']
dfs = [pd.read_csv(url) for url in URL_LIST]
df = pd.concat(dfs)
dj = folium.Map(location=[25.681137,-89.890137],
                tiles='Mapbox Bright', zoom_start=5)

for i in range(0,len(df)):
    folium.Marker([df.iloc[i]["Surface Latitude"],df.iloc[i]['Surface Longitude']], popup=df.iloc[i]['Well Name Suffix']).add_to(dj)
    dj.save("output1.html")
                  

   
    

