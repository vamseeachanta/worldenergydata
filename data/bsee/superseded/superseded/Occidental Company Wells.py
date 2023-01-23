import matplotlib.pyplot as plt
import pandas as pd
import pylab

URL_LIST = ['C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\0119gomwells\\csv files\\oxy1.csv', 'C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\0119gomwells\\csv files\\oxy2.csv', 'C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\0119gomwells\\csv files\\oxy3.csv']
dfs = [pd.read_csv(url) for url in URL_LIST]
df = pd.concat(dfs)
x = df["Company Name"]
y = df["Water Depth (feet)"]
print(x)
print(y)
##x1 = range(106)
##pylab.xticks(x1,x,rotation=90)
##plt.tight_layout()
##pylab.bar(x1,y,width=0.50,color="g")
##pylab.show()
##list = ['Occidental Petroleum Corporation','Oxy Petroleum, Inc.','OXY USA Inc.']
##
##
##for row in df:
##    if row == "Company Name":
##       for CompanyName in list:
##        x =  df[df[row] == CompanyName]["Company Name"]
##        y =  df[df[row] == CompanyName]["Water Depth (feet)"]
##        x1 = range(4)
##        pylab.xticks(x1,x,rotation=90)
##        pylab.plot(x1,y,"g")
##        pylab.show()
##        pass
##        x2 = range(5)
##        pylab.xticks(x2,x,rotation=90)
##        pylab.plot(x2,y,"g")
##        pylab.show()
##        pass
##    x3 = range(97)
##    pylab.xticks(x3,x,rotation=90)
##    pylab.plot(x3,y,"g")
##    pylab.show()
            
            

