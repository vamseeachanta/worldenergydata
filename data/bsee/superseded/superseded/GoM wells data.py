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
df.to_csv("D:\\mithra\\New folder\\day5\\jp1.csv",header=2)
GoM_Wells = pd.read_csv("D:\\mithra\\New folder\\day5\\jp1.csv",header=1)
GoM_Wells['COUNTER'] =1
GoM_Wells["wells"]=1
fig, ax = plt.subplots(figsize=(20,15))
##grouping data of two individual columns using pandas groupby
##unstack opertions for plotting grouping objects
##https://scentellegher.github.io/programming/2017/07/15/pandas-groupby-multiple-columns-plot.html
##http://nikgrozev.com/2015/07/01/reshaping-in-pandas-pivot-pivot-table-stack-and-unstack-explained-with-pictures/
GoM_Wellsplot = GoM_Wells.groupby(['COMPANY_NAME','BOTM_AREA_CODE']).count()['BOTM_BLOCK_NUMBER'].unstack().plot(ax=ax)
plt.tight_layout()
plt.setp(plt.xticks()[1], rotation=90, ha='right')
plt.title("COMPANIES OPERATING WELLS IN GoM IN PARTICULAR BLOCKS")
fig.savefig('E:\\mithra22\\Mithra_W\\reallife\\0119gomwells\\img files\\gomwellstotal3.png',dpi=800)
plt.show()
