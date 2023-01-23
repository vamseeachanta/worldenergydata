### -*- coding: utf-8 -*-
##"""
##Created on Sunday 19:45:17 2018
##
####@author: Manoj.Pydah
####"""

from __future__ import print_function  # Works only with 3+ version of python

import os.path

import xlrd
import xlwt

workingFile = xlrd.open_workbook('C:/Users/Manoj Pydah/Dropbox/0119 Programming/008 GoM Wells/Code/data/2016 Atlas Update.xlsx')      #open 2016 Sands data using XLRD
readSheet1 = workingFile.sheet_by_name(u'2016chronozones')              #Read Chronoze sheet
readSheet2 = workingFile.sheet_by_name(u'2016plays')                    #Read play sheet
readSheet3 = workingFile.sheet_by_name(u'2016sands_Public')             #Read Sands sheet
readSheet4 = workingFile.sheet_by_name(u'2016xref_oper-comp')
writingFile1 = xlwt.Workbook()                                           #Writing to excel file
writeSheet1 = writingFile1.add_sheet("Chronozone")                       #Writing Cronozone array to excel file
chronozoneList = []                                                     #Creating dummy Chronozone tuple to save to excel file

boemChronozone = readSheet1.col_values(0)                               #BOEM Names of Epoches list
uniChronozone = readSheet1.col_values(1)                                #Universal Epoches list
play = readSheet2.col_values(0)                                         #chronozones list
playtype = readSheet2.col_values(1)                                     #
wellapi = readSheet3.col_values(7)
wellapi1 = readSheet3.col_values(23)
##boemblock = readSheet4.col_values(2)
##blocknumber = readSheet4.col_values(3)
##wellapi2 = readSheet4.col_values(4)
palogeneEpochArray = ["Oligocene","Eocene","Paleocene","Tertiary"]      #Possible Epochs for lower Tertiary
####print (len(uniChronozone))
###loop for getting boem naming convention of epoches
for epochCount,palogeneEpoch in enumerate(palogeneEpochArray):
        for chronozoneCount,chronozoneSearch in enumerate(uniChronozone):
               if palogeneEpoch in chronozoneSearch:
                       print (chronozoneCount,chronozoneSearch)         #Palogene Epoch Chronozone search
                       chronozoneList.append(chronozoneSearch)          #Save the names of chronozones to list
writeSheet1.write(0,0,'chronozoneList')
writingFile1.save('C:/Users/Manoj Pydah/Dropbox/0119 Programming/008 GoM Wells/Code/calculations/Chrono.xls')

