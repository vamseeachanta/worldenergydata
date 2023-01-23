import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_csv("E:\\mithra22\\Mithra_W\\reallife\\0119gomwells\\csv files\\Boreholemain3.csv")
df['COUNTER'] =1
df["wells"]=1
fig, ax = plt.subplots(figsize=(20,15))
groups = df.groupby(['Company Name','Bottom Area']).count()['Bottom Block'].unstack().plot(ax=ax)
plt.tight_layout()
plt.setp(plt.xticks()[1], rotation=90, ha='right')
plt.title("COMPANIES OPERATING WELLS IN GoM IN PARTICULAR BLOCKS")
fig.savefig('E:\\mithra22\\Mithra_W\\reallife\\0119gomwells\\img files\\gomwellstotal2.png',dpi=800)
plt.show()
