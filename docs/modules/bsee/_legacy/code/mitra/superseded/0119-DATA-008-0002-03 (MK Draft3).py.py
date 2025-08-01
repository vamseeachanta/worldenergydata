from __future__ import print_function   #Works only with 3+ version of python
import os.path
import xlrd
import xlwt
import xlsxwriter
import csv
import folium
import pandas as pd
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
blocknaming = []
blocknumbering = []
operatordetails1 = []
leasenumber2 = []
boemChronozone = readSheet1.col_values(0)                               #BOEM Names of Epoches list
uniChronozone = readSheet1.col_values(1)                                #Universal Epoches list
play = readSheet2.col_values(0)                                         #chronozones list
playtype = readSheet2.col_values(2)
wellapi = readSheet3.col_values(7)
wellapi1 = readSheet3.col_values(20)
f = list(csv.reader(open('C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\Parameters_MK\\BoreholeRawData\\mv_boreholes.txt', 'r')))
WellLeaseData = list(csv.reader(open("C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\calculations\\LeaseOwnerRawData\\mv_lease_owners_main.txt",'r')))
CompanyData = list(csv.reader(open("C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\Parameters_MK\\CompanyRawData\\mv_companies_all.txt",'r')))
BoreholeRawData = pd.DataFrame(f)
BoreholeLeaseData = pd.DataFrame(WellLeaseData)
CompanyLeaseData = pd.DataFrame(CompanyData)
text = BoreholeRawData[0]
text3 = BoreholeRawData[6]
text1 = BoreholeRawData[21]
text2 = BoreholeRawData[22]
text4 = BoreholeRawData[3]
text5 = BoreholeLeaseData[0]
text6 = BoreholeRawData[4]
text7 = BoreholeRawData[5]
text8 = BoreholeLeaseData[1]
text9 = CompanyLeaseData[0] #company identity
text10 = CompanyLeaseData[2] #Company name data
text11 = CompanyLeaseData[3] #operator address


palogeneEpochArray = ["Oligocene","Eocene","Paleocene","Tertiary"]      #Possible Epochs for lower Tertiary

####print (len(uniChronozone))
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
                                                                                                       for wellcount,wellapinumbersearch in enumerate(text):
                                                                                                               if wellapinumber ==  wellapinumbersearch:
##                                                                                                                       print(wellapinumbersearch)
                                                                                                                       wellapinumber2.append(wellapinumbersearch)
                                                                                                                       for wells,latitude in enumerate(text1):
                                                                                                                               if wellcount == wells:
##                                                                                                                               print(latitude)
                                                                                                                                
                                                                                                                                for  wells1,longitude in enumerate(text2):
                                                                                                                                        if wells == wells1:
                                                                                                                                                
                                                                                                                                                for companyname,company in enumerate(text3):
                                                                                                                                                        if wells1 == companyname:
##                                                                                                                                                                print(latitude,company,longitude)
                                                                                                                                                               
                                                                                                                                                                for block,blockname in enumerate(text6):
                                                                                                                                                                        if companyname == block:
                                                                                                                                                                                for blocknames,blocknumber in enumerate(text7):
                                                                                                                                                                                        if block == blocknames:
                                                                                                                                                                                                for lease,leasenumber in enumerate(text4):
                                                                                                                                                                                                        if block == lease:
##                                                                                                                                                                                                                print(leasenumber)
                                                                                                                                                                                                                for bottomlease,leasedata in enumerate(text5):
                                                                                                                                                                                                                        if leasenumber == leasedata:
                                                                                                                                                                                                                                for Operatornumber,Operatordetails in enumerate(text8):
                                                                                                                                                                                                                                         if bottomlease == Operatornumber:
##                                                                                                                                                                                                                                                 print(Operatordetails)
                                                                                                                                                                                                                                                 for operatorlease,operatordata in enumerate(text9):
                                                                                                                                                                                                                                                         if Operatordetails == operatordata:
                                                                                                                                                                                                                                                                 for operatordata1,operatornum in enumerate(text10):
                                                                                                                                                                                                                                                                         if operatorlease == operatordata1:
##                                                                                                                                                                                                                                                                                 print(operatornum)
                                                                                                                                                                                                                                                                                 for companyaddress,operatorarea in enumerate(text11):
                                                                                                                                                                                                                                                                                         if operatordata1 == companyaddress:
                                                                                                                                                                                                                                                                                                 print(operatorarea,operatordata,leasenumber,latitude,blocknumber,blockname,longitude,company)
                                                                                                                                                                                                                                                                                                 surfacelatitude.append(latitude)
                                                                                                                                                                                                                                                                                                 surfacelongitude.append(longitude)
                                                                                                                                                                                                                                                                                                 companynames.append(company)                                                                                                                                                                                                                                                                                                 
                                                                                                                                                                                                                                                                                                 leasenumber1.append(operatornum)
                                                                                                                                                                                                                                                                                                 leasenumber2.append(operatordata)
                                                                                                                                                                                                                                                                                                 blocknaming.append(blockname)
                                                                                                                                                                                                                                                                                                 blocknumbering.append(blocknumber)
                                                                                                                                                                                                                                                                                                 operatordetails1.append(operatorarea)
                                                                                                                                                                                                                                                                         
                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                
                                                                                                                                                                                               
                                                                                                                                                                                                                                                                                                                                                                                                     
##                                                                                                                                                                       
##
###creating excel workbook from output calculations
writer = pd.ExcelWriter("gomwells.xlsx")
epoch  = pd.DataFrame.from_dict({'Chrono_Zone':chronozoneList,"Play_List":playList})
play1 = pd.DataFrame.from_dict({'Play_search':playnaming,"play_nature":playtypenature})
apinumber3 = pd.DataFrame.from_dict({'play_name':wellapinumber1,"wellapi":apinumber})
companynames1 = pd.DataFrame.from_dict({'BlockName':blocknaming,'BlockNumber':blocknumbering,'LeaseNumber':leasenumber2,'CompanyName':companynames,"OperatorDetail":operatordetails1,"Latitude":surfacelatitude,"Longitude":surfacelongitude})
epoch.to_excel(writer,sheet_name= "Chrono1", header=True, index=False) # creating excel sheet for chronozone data
play1.to_excel(writer,sheet_name= "plays", header=True, index=False) # creating excel sheet for plays data
apinumber3.to_excel(writer,sheet_name= "wellapinumber", header=True, index=False) # creating excel sheet for wellapinumber
companynames1.to_excel(writer,sheet_name= "Lowertertiarywells", header=True, index=False) # creating excel sheet saving company latitude and longitude details of wells

                                                      

####
####                                                      
##

