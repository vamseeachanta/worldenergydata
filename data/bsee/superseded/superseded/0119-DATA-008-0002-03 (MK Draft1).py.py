### -*- coding: utf-8 -*-
##"""
##Created on Sunday 17:19:15 2018
##
####@author: Manoj.Pydah
####"""
####

import xlrd

workingFile = xlrd.open_workbook('2016 Atlas Update.xlsx')  #open 2016 Sands data using XLRD
sheet1 = workingFile.sheet_by_name(u'2016chronozones')  #Read Chronoze sheet
sheet2 = workingFile.sheet_by_name(u'2016plays')  #Read play sheet
sheet3 = workingFile.sheet_by_name(u'2016sands_Public')  #Read Sands sheet
boemChronozone = sheet1.col_values(0)    #BOEM Names of Epoches list
uniChronozone = sheet1.col_values(1)     #Universal Epoches list
play = sheet2.col_values(0)
playtype = sheet2.col_values(2)
wellapi = sheet3.col_values(7)
wellapi1 = sheet3.col_values(20)
palogeneEpochArray = ['Oligocene', 'Eocene', 'Paleocene', 'Tertiary']

##print (len(uniChronozone))
#loop for getting boem naming convention of epoches
for m,i in enumerate(palogeneEpochArray):
        print(m,i)
        for n,j in enumerate(uniChronozone):
                if i in j:
                        print(n,j)
                        for o,k in enumerate(boemChronozone):
                                if   n == o:
                                        for p,l in enumerate(play):
                                                if k == l:
                                                        print(l)
                                                        for r,s in enumerate(playtype):
                                                                if p == r:
                                                                        print(s)
                                                                        for q,t in enumerate(wellapi1):
                                                                                if  s == t:
                                                                                        for u,v in enumerate(wellapi):
                                                                                                if q == u :
                                                                                                        
                                                                                                        print(t,v)


                       
                        


                                                                        
