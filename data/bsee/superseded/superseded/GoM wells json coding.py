import csv

import matplotlib.pyplot as plt
import pandas as pd

path = 'D:\\mithra\\New folder\\day5\\BoreholeRawData\\'
file = 'mv_boreholes.txt'
f = open(path+file,'rt')
reader = csv.reader(f)
##After getting the contents i have put them in a list
csv_list = []
for line in reader:
    csv_list.append(line)
f.close()
##creating dataframe to the list 
df = pd.DataFrame(csv_list)
#converting dataframe to json format
df.to_json("D:\\mithra\\New folder\\day5\\jp2.json",orient='index')











