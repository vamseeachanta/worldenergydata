### -*- coding: utf-8 -*-
##"""
##Created on Sunday 17:19:15 2018
##
####@author: Manoj.Pydah
####"""
##
import csv

import pandas as pd
import xlrd

workingFile = xlrd.open_workbook('2016 Atlas Update.xlsx')  #open 2016 Sands data using XLRD
sheet1 = workingFile.sheet_by_name(u'2016chronozones')  #Read Chronoze sheet
sheet2 = workingFile.sheet_by_name(u'2016plays')  #Read play sheet
sheet3 = workingFile.sheet_by_name(u'2016sands_Public')  #Read Sands sheet
sheet4 = workingFile.sheet_by_name(u'2016xref_oper-comp')
boemChronozone = sheet1.col_values(0)    #BOEM Names of Epoches list
uniChronozone = sheet1.col_values(1)     #Universal Epoches list
play = sheet2.col_values(0)  #chronozones list
playtype = sheet2.col_values(1) #
wellapi = sheet3.col_values(7)
wellapi1 = sheet3.col_values(23)
##boemblock = sheet4.col_values(2)
##blocknumber = sheet4.col_values(3)
####wellapi2 = sheet4.col_values(4)
palogeneEpochArray = ["Oligocene","Eocene","Paleocene","Tertiary"]
##f = open('C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\data\\BoreholeRawData\\mv_boreholes.txt','r')
f = list(csv.reader(open('C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\data\\BoreholeRawData\\mv_boreholes.txt', 'r')))
BoreholeRawData = pd.DataFrame(f)
text = BoreholeRawData[0]
text3 = BoreholeRawData[6]
text1 = BoreholeRawData[21]
text2 = BoreholeRawData[22]
######print (len(uniChronozone))
###loop for getting boem naming convention of epoches
for epochCount,palogeneEpoch in enumerate(palogeneEpochArray):
        for chronozoneCount,chronozoneSearch in enumerate(uniChronozone):
               if palogeneEpoch in chronozoneSearch:
#                       print (chronozoneSearch) #Palogene Epoch Chronozone search
                       for boemchronozoneCount,boemchronozoneNaming in enumerate(boemChronozone):
                               if   chronozoneCount == boemchronozoneCount:
##                                       print(boemchronozoneCount, chronozoneSearch, boemchronozoneNaming) # finding boem naming in chronozone
                                       for playCount,playsearch in enumerate(play):
                                               if boemchronozoneNaming == playsearch:
##                                                       print(playsearch) # finding  play naming 
                                                       for playsearchcount,playnature in enumerate(playtype): 
                                                               if playCount == playsearchcount:
##                                                                       print(playnature) # finding play type in choronozone
                                                                       for wellapicount,wellapisearch in enumerate(wellapi1):
                                                                               if playnature == wellapisearch:
##                                                                                       print(wellapisearch) #finding well api
                                                                                       for wellapisearchcount,wellapinumber in enumerate(wellapi):
                                                                                               if wellapicount == wellapisearchcount:
##                                                                                                        print(wellapisearch,wellapinumber) # finding well api number
                                                                                                   for wellcount,wellapinumbersearch in enumerate(text):
                                                                                                       if wellapinumber ==  wellapinumbersearch:
##                                                                                                               print(wellapinumbersearch,wellcount)
                                                                                                               for wells,latitude in enumerate(text1):
                                                                                                                       if wellcount == wells:
##                                                                                                                               print(latitude)
                                                                                                                               for  wells1,longitude in enumerate(text2):
                                                                                                                                       if wells == wells1:
                                                                                                                                               for companyname,company in enumerate(text3):
                                                                                                                                                       if wells1 == companyname:
                                                                                                                                                               print(latitude,company,longitude)

                                                                                                                                                
dj1 = pd.DataFrame({"Company Name":(company),
                    "Surface Latitude":(latitude),
                    'Surface Longitude':(longitude)},index=[0])
dj1.to_csv("E:\\mithra22\\Mithra_W\\reallife\\0119gomwells\\csv files\\output6.csv", sep=',')
                                                                                       


##for m,i in enumerate(palogeneEpochArray):
####        print(m,i)
##        for n,j in enumerate(uniChronozone):
##               if i in j:
##                      for o,k in enumerate(boemChronozone):
##                             if   n == o:
####                                    print(n,j,k)
##                                    for p,l in enumerate(play):
##                                            if k == l:
####                                                   print(l)
##                                                   for r,s in enumerate(playtype):
##                                                           if p == r:
####                                                                   print(s)
##                                                                   for q,t in enumerate(wellapi1):
##                                                                           if  s == t:
####                                                                                   print(t)
##                                                                                    for u,v in enumerate(wellapi):
##                                                                                            if q == u :
##
##                                                                                                    print(t,v)
                                                                                                                                                                                           
##                                                                                                    for x,y in enumerate(wellapi2):
##                                                                                                            if v == y:
##                                                                                                                    for z,a in enumerate(boemblock):
##                                                                                                                            if x == z:
##                                                                                                                                    print(y,a)
                                                                                                                    
                                                                                                    

                                   
                                   


