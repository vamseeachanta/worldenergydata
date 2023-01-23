###Data Source download from browser
##import urllib.request
##url = 'https://www.data.bsee.gov/Well/Borehole/Default.aspx'
##response = urllib.request.urlopen(url)
###the code downloads the file contents into the variable data from http link
##data = response.read()      
### a `str`; this step can't be used if data is binary
##text = data.decode('utf-8') 

import matplotlib.pyplot as plt
#coding for GoM Wells
import pandas as pd

GoM_Wellsdata = pd.read_csv("C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CSV\\Boreholemain4.csv")
GoM_Wellsdata['COUNTER'] =1
GoM_Wellsdata["wells"]=1
fig, ax = plt.subplots(figsize=(20,15))
##grouping data of two individual columns using pandas groupby
##unstack opertions for plotting grouping objects
##https://scentellegher.github.io/programming/2017/07/15/pandas-groupby-multiple-columns-plot.html
##http://nikgrozev.com/2015/07/01/reshaping-in-pandas-pivot-pivot-table-stack-and-unstack-explained-with-pictures/
GoM_Wellsplot = GoM_Wellsdata.groupby(['Company Name','Bottom Area']).count()['Bottom Block'].unstack().plot(ax=ax)
plt.tight_layout()
plt.setp(plt.xticks()[1], rotation=90, ha='right')
plt.title("COMPANIES OPERATING WELLS IN GoM IN PARTICULAR BLOCKS")
fig.savefig('E:\\mithra22\\Mithra_W\\reallife\\0119gomwells\\img files\\gomwellstotal2.png',dpi=800)
plt.show()
