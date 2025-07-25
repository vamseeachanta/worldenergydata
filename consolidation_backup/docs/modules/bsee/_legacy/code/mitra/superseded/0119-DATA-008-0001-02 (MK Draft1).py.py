### -*- coding: utf-8 -*-
##"""
##Created on Sunday 19:45:17 2018
##
####@author: Manoj.Pydah
####"""

import xlrd
import xlwt

workingFile = xlrd.open_workbook('2016 Atlas Update.xlsx')      #open 2016 Sands data using XLRD
sheet1 = workingFile.sheet_by_name(u'2016chronozones')          #Read Chronoze sheet
sheet2 = workingFile.sheet_by_name(u'2016plays')                #Read play sheet
sheet3 = workingFile.sheet_by_name(u'2016sands_Public')         #Read Sands sheet
sheet4 = workingFile.sheet_by_name(u'2016xref_oper-comp')
boemChronozone = sheet1.col_values(0)                           #BOEM Names of Epoches list
uniChronozone = sheet1.col_values(1)                            #Universal Epoches list
play = sheet2.col_values(0)                                     #chronozones list
playtype = sheet2.col_values(1)                                 #
wellapi = sheet3.col_values(7)
wellapi1 = sheet3.col_values(23)
##boemblock = sheet4.col_values(2)
##blocknumber = sheet4.col_values(3)
##wellapi2 = sheet4.col_values(4)
palogeneEpochArray = ["Oligocene","Eocene","Paleocene","Tertiary"]
####print (len(uniChronozone))
###loop for getting boem naming convention of epoches
for epochCount,palogeneEpoch in enumerate(palogeneEpochArray):
        for chronozoneCount,chronozoneSearch in enumerate(uniChronozone):
               if palogeneEpoch in chronozoneSearch:
#                       print (chronozoneSearch) #Palogene Epoch Chronozone search
                       for boemhronozoneCount,boemcronozoneNaming in enumerate(boemChronozone):
                               if   chronozoneCount == boemhronozoneCount:
                                       print(boemhronozoneCount, chronozoneSearch, boemcronozoneNaming) # finding boem naming in cronozone
#                                       for p,l in enumerate(play):
#                                            if k == l:
#                                                   for r,s in enumerate(playtype):
#                                                           if p == r:
#                                                                   for q,t in enumerate(wellapi1):
#                                                                           if  s == t:
#                                                                                   for u,v in enumerate(wellapi):
#                                                                                           if q == u :
#
