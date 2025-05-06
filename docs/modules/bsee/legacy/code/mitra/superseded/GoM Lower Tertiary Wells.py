
import pandas as pd
URL_LIST = ["C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CSV\\superseded\\0119-CAL-008-0001-01-Alaminos Canyas.csv",
            "C:\\Users\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CSV\\superseded\\0119-CAL-008-0001-02-Garden Bank.csv",
            "C:\\Users\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CSV\\superseded\\0119-CAL-008-0001-03-Green Canyon.csv",
            "C:\\Users\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CSV\\superseded\\0119-CAL-008-0001-04-keathely Canyon.csv",
            "C:\\Users\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CSV\\superseded\\0119-CAL-008-0001-05-Port Isabel.csv",
            "C:\\Users\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CSV\\superseded\\0119-CAL-008-0001-06-se.csv",
            "C:\\Users\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CSV\\superseded\\0119-CAL-008-0001-07-Walker Ridge.csv"]
dfs = [pd.read_csv(url) for url in URL_LIST]
df = pd.concat(dfs)
list = [600,903,857,818,859,739,812,813,814,
        900,901,206,469,678,759,544,969,51,205,249,
        250,425,426,470,959,785,736,292,872,102,525,39,807]
x2 = []
for row in df:
    if row =='Bottom Block':
        for i in list:
            x =  df[df[row] == i]["Company Name"]
            y =  df[df[row] == i]["Water Depth (feet)"]
            x2.append(x)
         
          
            
        
