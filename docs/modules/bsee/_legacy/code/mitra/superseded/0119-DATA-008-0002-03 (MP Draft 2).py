from __future__ import print_function                                   #Works only with 3+ version of python
import os.path
import xlsxwriter
import csv
import pandas as pd
import io
workingFile = '2016 Atlas Update.xlsx'                                                    #open 2016 Sands data using XLRD
readSheet1 = pd.read_excel(workingFile,sheetname='2016chronozones',header=None)              #Read Chronoze sheet
readSheet2 = pd.read_excel(workingFile,sheetname='2016plays',header=None)                    #Read play sheet
readSheet3 = pd.read_excel(workingFile,sheetname='2016sands_Public',header=None)             #Read Sands sheet
readSheet4 = pd.read_excel(workingFile,sheetname='2016xref_oper-comp',header=None)
chronozoneList = []                                                     #Creating dummy Chronozone tuple to save to excel file
playList = []                                                           #Creating dummy playList tuple to save to excel file
playNaming = []                                                         #Creating dummy playNaming tuple to save to excel file
playtypeNature = []                                                     #Creating dummy playtypeNature tuple to save to excel file
wellapiNumber1 = []                                                     #Creating dummy wellapinumber tuple to save to excel file
apiNumber = []
surfaceLatitude = []                                                    #Creating dummy surfacelatitude tuple to save to excel file
surfaceLongitude = []                                                   #Creating dummy Surface longitude tuple to save to excel file
companyNames = []
wellapiNumber2 = []
leaseNumber1 = []                                                       #Creating dummy leasenumber tuple to save to excel file
blockNaming = []                                                        #Creating dummy blockname tuple to save to excel file
blockNumbering = []                                                     #Creating dummy blocknumber tuple to save to excel file
boemChronozone = readSheet1[readSheet1.columns[0]]                                          #BOEM Names of Epoches list
uniChronozone = readSheet1[readSheet1.columns[1]]                                           #Universal Epoches list
Play = readSheet2[readSheet2.columns[0]]                                                    #chronozones list
playType = readSheet2[readSheet2.columns[2]]
wellApi = readSheet3[readSheet3.columns[7]]
wellApi1 = readSheet3[readSheet3.columns[20]]
boreholeData = list(csv.reader(open("J:\\008 GoM Wells\\CAL\\boreholeRawdata\\mv_boreholes.txt", 'r'))) # open BoreholeData using Csv
boreholeRawdata = pd.DataFrame(boreholeData)
wellAPINumberColumn = boreholeRawdata[0]                                 #Well API number column
operatorColumn = boreholeRawdata[6]                                      #Operating companies Column 
latitudeColumn = boreholeRawdata[21]                                     #Well latitude data
longitudeColumn = boreholeRawdata[22]                                    #Well longitude data
bottomLeaseColumn = boreholeRawdata[3]                                   #Well Bottom lease number data
blockColumn = boreholeRawdata[4]                                         #blocks data
blockNumberColumn = boreholeRawdata[5]                                   #blocks number data

paleogeneEpochArray = ["Oligocene","Eocene","Paleocene","Tertiary", "Paleogene"]       #Possible Epochs for lower Tertiary

####print (len(uniChronozone))
###loop for getting boem naming convention of epoches
for epochCount,paleogeneEpoch in enumerate(paleogeneEpochArray):
    for chronozoneCount,chronozoneSearch in enumerate(uniChronozone):
        if paleogeneEpoch in chronozoneSearch:
##            print (chronozoneCount,chronozoneSearch)#Palogene Epoch Chronozone search
            chronozoneList.append(chronozoneSearch)
            for boemchronozoneCount,boemchronozoneNaming in enumerate(boemChronozone):
                if chronozoneCount == boemchronozoneCount:
##                    print(boemchronozoneCount, chronozoneSearch, boemchronozoneNaming) # finding boem naming in chronozone
                    playList.append(boemchronozoneNaming)
                    for playCount,playsearch in enumerate(Play):
                        if boemchronozoneNaming == playsearch:
##                            print(playsearch) # finding  play naming
                            playNaming.append(playsearch)
                            for playsearchcount,playnature in enumerate(playType):
                                if playCount == playsearchcount:
##                                    print(playnature,playsearch) # finding play type in choronozone
                                    playtypeNature.append(playnature)
                                    for wellapicount,wellapisearch in enumerate(wellApi1):
                                        if playnature == wellapisearch:
##                                            print(wellapisearch) #finding well api
                                            wellapiNumber1.append(wellapisearch)
                                            for wellapisearchcount,wellapinumber in enumerate(wellApi):
                                                if wellapicount == wellapisearchcount:
##                                                    print(wellapisearch,wellapinumber) # finding well api number
                                                    apiNumber.append(wellapinumber)
                                                    for wellcount,wellapinumbersearch in enumerate(wellAPINumberColumn):#comparing well api number
                                                        if wellapinumber ==  wellapinumbersearch:
##                                                            print(wellapinumbersearch)
                                                            wellapiNumber2.append(wellapinumbersearch)
                                                            for wells,latitude in enumerate(latitudeColumn): #finding latitude of wells
                                                                if wellcount == wells:
##                                                                    print(latitude)
                                                                    surfaceLatitude.append(latitude)
                                                                    for  wells1,longitude in enumerate(longitudeColumn): #finding longitude of the wells
                                                                        if wells == wells1:
                                                                            surfaceLongitude.append(longitude)
                                                                            for companyname,company in enumerate(operatorColumn):
                                                                                if wells1 == companyname:
##                                                                                    print(latitude,company,longitude)
                                                                                    companyNames.append(company)
                                                                                    for block,blockname in enumerate(blockColumn): #finding block names
                                                                                        if companyname == block:
                                                                                            blockNaming.append(blockname)
                                                                                            for blocknames,blocknumber in enumerate(blockNumberColumn): #finding block number
                                                                                                if block == blocknames:
                                                                                                    blockNumbering.append(blocknumber)
                                                                                                    for lease,leasenumber in enumerate(bottomLeaseColumn): #finding leasenumber
                                                                                                        if block == lease:
                                                                                                            print(leasenumber)
                                                                                                            leaseNumber1.append(leasenumber)
                                                                                                           
                                                                                                           
                                                                                                           
                                                                                                            
                                                                                                           
                                                                                                           
##
#creating excel workbook from output calculations
writer = pd.ExcelWriter("gomwells.xlsx")
Epoch  = pd.DataFrame.from_dict({'Chrono_Zone':chronozoneList,"Play_List":playList})
Play1 = pd.DataFrame.from_dict({'Play_search':playNaming,"play_nature":playtypeNature})
apiNumber3 = pd.DataFrame.from_dict({'play_name':wellapiNumber1,"wellapi":apiNumber})
Companynames1 = pd.DataFrame.from_dict({'BlockName':blockNaming,'BlockNumber':blockNumbering,'LeaseNumber':leaseNumber1,'CompanyName':companyNames,"Latitude":surfaceLatitude,"Longitude":surfaceLongitude})
Epoch.to_excel(writer,sheet_name= "Chrono1", header=True, index=False)                        # creating excel sheet for chronozone data
Play1.to_excel(writer,sheet_name= "plays", header=True, index=False)                          # creating excel sheet for plays data
apiNumber3.to_excel(writer,sheet_name= "wellapinumber", header=True, index=False)             # creating excel sheet for wellapinumber
Companynames1.to_excel(writer,sheet_name= "Lowertertiarywells", header=True, index=False)     # creating excel sheet saving company latitude and longitude details of wells

                                                      

##
####                                                      
##
  
