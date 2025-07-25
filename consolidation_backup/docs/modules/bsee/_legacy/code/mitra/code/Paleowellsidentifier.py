from random import random
import pandas as pd
f = open("C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\data\\gepaldmp_all\\gepaldmp_Paleo.txt",'r')

Epoch = ["Paleocene","Eocene","Oligocene"]
for era,era1 in enumerate(f):
        for era2,era3 in enumerate(Epoch):
                if era3 in era1:
##                        print(era1)
                        break
                

with open("C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\calculations\\PaleogeneEpochs.txt",'a') as f1:
        f1.write(era1)


f2 = open("C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\calculations\\PaleogeneEpochs.txt",'r')
fwidths = [1,12,2,2,5,5,3,2,100,3,2,1]		                                #width data and headers from pdf in the extract, refer page 2
df = pd.read_fwf(f2,widths = fwidths, names = ['Record Type',
                                               'API Well Number',
                                               'Paleo Report ID Number',
                                               'Total Number of Reports for API',
                                               'Measured Depth',
                                               'True Vertical Depth',
                                               'Definite/Possible',
                                               'At/In',
                                               'Paleo Age',
                                               'Definite/Possible',
                                               'At/In',
                                               'Ecozone'])

##print(df.shape)
df.to_csv("C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\calculations\\Paleowells.csv")

