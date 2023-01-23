from __future__ import print_function  # Works only with 3+ version of python

import csv
import os.path

import folium
import pandas as pd
import xlrd
import xlsxwriter
import xlwt
from folium.plugins import MarkerCluster

workingFile = xlrd.open_workbook('2016 Atlas Update.xlsx')      #open 2016 Sands data using XLRD
readSheet1 = workingFile.sheet_by_name(u'2016chronozones')              #Read Chronoze sheet
readSheet2 = workingFile.sheet_by_name(u'2016plays')                    #Read play sheet
readSheet3 = workingFile.sheet_by_name(u'2016sands_Public')             #Read Sands sheet
readSheet4 = workingFile.sheet_by_name(u'2016xref_oper-comp')
chronozoneList = []                                                     #Creating dummy Chronozone tuple to save to excel file
playList = []
playnaming = []
playtypenature = []
wellapinumber1 = []
apinumber = []
surfacelatitude = []
surfacelongitude = []
companynames = []
wellapinumber2 = []
leasenumber1 = []
leasenumber2 = []
blocknaming = []
blocknumbering = []
operatordetails1 = []
boemChronozone = readSheet1.col_values(0)                               #BOEM Names of Epoches list
uniChronozone = readSheet1.col_values(1)                                #Universal Epoches list
play = readSheet2.col_values(0)                                         #chronozones list
playtype = readSheet2.col_values(2)
wellapi = readSheet3.col_values(7)
wellapi1 = readSheet3.col_values(20)
Boreholedata = list(csv.reader(open('C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\data\\BoreholeRawData\\mv_boreholes.txt', 'r'))) # open BoreholeData using Csv
WellLeaseData = list(csv.reader(open("C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\calculations\\LeaseOwnerRawData\\mv_lease_owners_main.txt",'r'))) #open leasefiledata using csv
CompanyData = list(csv.reader(open("C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\Parameters_MK\\CompanyRawData\\mv_companies_all.txt",'r'))) #open companydata using csv
BoreholeRawData = pd.DataFrame(Boreholedata) #creating dataframe for boreholedata
BoreholeLeaseData = pd.DataFrame(WellLeaseData) #creating dataframe for lease data
CompanyLeaseData = pd.DataFrame(CompanyData)  #creating dataframe for Company details
text = BoreholeRawData[0] #Well API number column
text1 = BoreholeRawData[21] #Well latitude data
text2 = BoreholeRawData[22] # Well longitude data
text12 = BoreholeRawData[6]
text4 = BoreholeRawData[3]   #Well Bottom lease number data
text5 = BoreholeLeaseData[0] #Bottom lease number data of well
text6 = BoreholeLeaseData[1] #Company mms leasenumber
text3 = BoreholeLeaseData[2] #Operating companies Column 
text7 = CompanyLeaseData[0] #company identity
text8 = CompanyLeaseData[2] #Company name data
text9 = CompanyLeaseData[3] #operator address
text10 = BoreholeRawData[4] #block data
text11 = BoreholeRawData[5] #block number data
palogeneEpochArray = ["Oligocene","Eocene","Paleocene","Tertiary"]      #Possible Epochs for lower Tertiary

###loop for getting boem naming convention of epoches
for epochCount,palogeneEpoch in enumerate(palogeneEpochArray):
        for chronozoneCount,chronozoneSearch in enumerate(uniChronozone):
               if palogeneEpoch in chronozoneSearch:
##                       print (chronozoneCount,chronozoneSearch)#Palogene Epoch Chronozone search
                       chronozoneList.append(chronozoneSearch)
                       for boemchronozoneCount,boemchronozoneNaming in enumerate(boemChronozone):
                               if   chronozoneCount == boemchronozoneCount:
##                                       print(boemchronozoneCount, chronozoneSearch, boemchronozoneNaming) # finding boem naming in chronozone
                                       playList.append(boemchronozoneNaming)
                                       for playCount,playsearch in enumerate(play):
                                               if boemchronozoneNaming == playsearch:
##                                                       print(playsearch) # finding  play naming
                                                       playnaming.append(playsearch)
                                                       for playsearchcount,playnature in enumerate(playtype):
                                                               if playCount == playsearchcount:
##                                                                       print(playnature,playsearch) # finding play type in choronozone
                                                                       playtypenature.append(playnature)
                                                                       for wellapicount,wellapisearch in enumerate(wellapi1):
                                                                               if playnature == wellapisearch:
##                                                                                       print(wellapisearch) #finding well api
                                                                                       wellapinumber1.append(wellapisearch)
                                                                                       for wellapisearchcount,wellapinumber in enumerate(wellapi):
                                                                                               if wellapicount == wellapisearchcount:
##                                                                                                      print(wellapisearch,wellapinumber) # finding well api number
                                                                                                       apinumber.append(wellapinumber)
                                                                                                       for wellcount,wellapinumbersearch in enumerate(text): #comparing well API numbers
                                                                                                               if wellapinumber ==  wellapinumbersearch:
##                                                                                                                       print(wellapinumbersearch)
                                                                                                                       wellapinumber2.append(wellapinumbersearch)
                                                                                                                       for lease,leasenumber in enumerate(text4): # finding leases
                                                                                                                               if wellcount == lease:
                                                                                                                                       print(leasenumber)
                                                                                                                                       for bottomlease,leasedata in enumerate(text5):
                                                                                                                                               if leasenumber == leasedata:
                                                                                                                                                       print(leasedata,leasenumber)
                                                                                                                                                       leasenumber1.append(leasedata)
                                                                                                                                                       for companyname,company in enumerate(text12): #finding operating companies
                                                                                                                                                               if bottomlease == companyname:
                                                                                                                                                                       print(company)
                                                                                                                                                                       companynames.append(company)
##                                                                                                                                                                       for wells,latitude in enumerate(text1): #finding well latitude
##                                                                                                                                                                               if companyname == wells:
##                                                                                                                                                                                       print(latitude)
##                                                                                                                                                                                       surfacelatitude.append(latitude)
##                                                                                                                                                                                       for  wells1,longitude in enumerate(text2): #finding well longitude
##                                                                                                                                                                                               if wells == wells1:
##                                                                                                                                                                                                       surfacelongitude.append(longitude)
##                                                                                                                                                                                           
##                                                                                                                                                                                                   
                                                                                                                                                                                                           
                                                                                                                                                                                                           
##                                                                                                                                                                                                           for block,blockname in enumerate(text10):
##                                                                                                                                                                                                                   if companyname == block:
##                                                                                                                                                                                                                           blocknaming.append(blockname)
##                                                                                                                                                                                                                           for blocknames,blocknumber in enumerate(text11):
##                                                                                                                                                                                                                                   if block == blocknames:
##                                                                                                                                                                                                                                           blocknumbering.append(blocknumber)
####                                                                                                                                                                                                                                           print(blocknumber,blockname)
##                                                                                                                                                                                                                                           for companyleasenumber,mmsleasenumber in enumerate(text6):
##                                                                                                                                                                                                                                                   if blocknames == companyleasenumber:
####                                                                                                                                                                                                                                                           print(mmsleasenumber)
##                                                                                                                                                                                                                                                           leasenumber2.append(mmsleasenumber)
##                                                                                                                                                                                                                                                           for Operatornumber,Operatordetails in enumerate(text7):
##                                                                                                                                                                                                                                                                   if mmsleasenumber == Operatordetails:
##                                                                                                                                                                                                                                                                          for operatorlease,operatordata in enumerate(text8):
##                                                                                                                                                                                                                                                                               if Operatornumber == operatorlease:
##                                                                                                                                                                                                                                                                                       for operatordata1,operatoraddress in enumerate(text9):
##                                                                                                                                                                                                                                                                                               if operatorlease == operatordata1:
####                                                                                                                                                                                                                                                                                                       print(Operatordetails,operatordata,operatoraddress)
##                                                                                                                                                                                                                                                                                                       operatordetails1.append(operatoraddress)
###creating excel workbook from output calculations
##writer = pd.ExcelWriter("gomwells.xlsx")
##epoch  = pd.DataFrame.from_dict({'Chrono_Zone':chronozoneList,"Play_List":playList})
##play1 = pd.DataFrame.from_dict({'Play_search':playnaming,"play_nature":playtypenature})
##apinumber3 = pd.DataFrame.from_dict({'play_name':wellapinumber1,"wellapi":apinumber})
##Activewells = pd.DataFrame.from_dict({'BlockName':blocknaming,'BlockNumber':blocknumbering,'CompanyName':companynames,'LeaseNumber':leasenumber1,"CompanyNumber":leasenumber2,"OperatorDetail":operatordetails1,"Latitude":surfacelatitude,"Longitude":surfacelongitude})
##epoch.to_excel(writer,sheet_name= "Chrono1", header=True, index=False) # creating excel sheet for chronozone data
##play1.to_excel(writer,sheet_name= "plays", header=True, index=False) # creating excel sheet for plays data
##apinumber3.to_excel(writer,sheet_name= "wellapinumber", header=True, index=False) # creating excel sheet for wellapinumber
##Activewells.to_excel(writer,sheet_name= "Lowertertiarywells", header=True, index=False) # creating excel sheet saving company latitude and longitude details of wells
##
##                                                      
##
##
####
##
