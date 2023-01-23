import csv
from itertools import groupby

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
import pylab
from matplotlib.widgets import MultiCursor
from pylab import figure, np, show

plt.style.use("ggplot")
df = pd.read_csv('C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\csv files\\Borehole (2).csv')
y = df["Company Name"].sort_values()
x =  []
y1 = []
for word,duplicates in groupby(sorted(y)):
    count = len(list(duplicates))
    x .append(word)
    y1.append(count)
    
##print(x)
##print(y1)

   
xx = range(425)
box = dict(facecolor='Blue', pad=5, alpha=0.20)
fig = plt.figure(num=None,figsize=(10,10))

ax1=fig.add_subplot(111)
ax1.set_title('Well Strategy')
ax1.set_xlabel('COMPANY NAME', bbox=box)
ax1.set_ylabel('WELLS OWNED', bbox=box)

pylab.xticks(xx,x,rotation=90)

ax1.plot(xx,y1,color="red")

pylab.tight_layout()
plt.savefig('well STATS1',dpi=800)
plt.show()


