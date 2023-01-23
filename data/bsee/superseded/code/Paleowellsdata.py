import csv
from itertools import groupby

import xlsxwriter
from Paleowellsidentifier import *

boreholeData = list(csv.reader(open("C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\data\\BoreholeRawData\\mv_boreholes.txt", 'r'))) # open BoreholeData using Csv
boreholeRawdata = pd.DataFrame(boreholeData)
wellapinumberColumn = boreholeRawdata[0]                                 #Well API number column
operatorColumn = boreholeRawdata[6]                                      #Operating companies Column 
latitudeColumn = boreholeRawdata[21]                                     #Well latitude data
longitudeColumn = boreholeRawdata[22]                                    #Well longitude data
bottomLeaseColumn = boreholeRawdata[3]                                   #Well Bottom lease number data
blockColumn = boreholeRawdata[4]                                         #blocks data
blockNumberColumn = boreholeRawdata[5]                                   #blocks number data
wellNature = boreholeRawdata[16]                                         #well status data column
surfaceLatitude = []                                                    #Creating dummy surfacelatitude tuple to save to excel file
surfaceLongitude = []                                                   #Creating dummy Surface longitude tuple to save to excel file
companyNames = []
wellapiNumber = []
leaseNumber1 = []                                                       #Creating dummy leasenumber tuple to save to excel file
blockNaming = []                                                        #Creating dummy blockname tuple to save to excel file
blockNumbering = []                                                     #Creating dummy blocknumber tuple to save to excel file
wellStatus = []                                                         #Creating dummy status code tuple to save well excel file
paleoWells = pd.read_csv("C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\calculations\\Paleowells.csv")
apiNumber = sorted(set(paleoWells["API Well Number"].astype(str)))

for wellapisearchcount,wellapinumber in enumerate(apiNumber):
    for wellcount,wellapinumbersearch in enumerate(wellapinumberColumn):#comparing well api numbe):
        if wellapinumber == wellapinumbersearch:
##            print(wellapinumbersearch)
            wellapiNumber.append(wellapinumbersearch)
            for wells,latitude in enumerate(latitudeColumn): #finding latitude of wells
                if wellcount == wells:
##                  print(latitude)
                    surfaceLatitude.append(latitude)
                    for  wells1,longitude in enumerate(longitudeColumn): #finding longitude of the wells
                         if wells == wells1:
                             surfaceLongitude.append(longitude)
                             for companyname,company in enumerate(operatorColumn):
                                 if wells1 == companyname:
##                                     print(latitude,company,longitude)
                                     companyNames.append(company)
                                     for block,blockname in enumerate(blockColumn): #finding block names
                                         if companyname == block:
                                             blockNaming.append(blockname)
                                             for blocknames,blocknumber in enumerate(blockNumberColumn): #finding block number
                                                 if block == blocknames:
                                                     blockNumbering.append(blocknumber)
                                                     for status,nature in enumerate(wellNature):
                                                         if blocknames == status:
                                                             wellStatus.append(nature)
                                                             for lease,leasenumber in enumerate(bottomLeaseColumn): #finding leasenumber
                                                                 if status == lease:
##                                                                     print(leasenumber)
                                                                     leaseNumber1.append(leasenumber)                                                                                                           

##            
writer = pd.ExcelWriter("C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\calculations\\Paleogenewells.xlsx")
wellsdata = pd.DataFrame.from_dict({'WellAPI': wellapiNumber,'BlockName':blockNaming,'BlockNumber':blockNumbering,'WellStatus':wellStatus,'LeaseNumber':leaseNumber1,'CompanyName':companyNames,"Latitude":surfaceLatitude,"Longitude":surfaceLongitude})                               
wellsdata.to_excel(writer,sheet_name= "Lowertertiarywells", header=True, index=False)     # creating excel sheet saving company latitude and longitude details of wells

##


