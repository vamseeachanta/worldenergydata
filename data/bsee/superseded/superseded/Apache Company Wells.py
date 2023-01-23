import matplotlib.pyplot as plt
import pandas as pd
import pylab

URL_LIST = ["C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\0119gomwells\\csv files\\apache1 (1).csv",
            "C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\0119gomwells\\csv files\\apache1 (2).csv",
            "C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\0119gomwells\\csv files\\apache1 (3).csv"]
dfs = [pd.read_csv(url) for url in URL_LIST]
df = pd.concat(dfs)
x = df["Company Name"]
y = df["Water Depth (feet)"]
x1 = range(2718)
pylab.xticks(x1,x,rotation=90)
plt.tight_layout()
plt.plot(x1,y,color="g")
pylab.show()
