from Lowertertiary import *

WellLeaseData = list(csv.reader(open("C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\test\\LeaseOwnerRawData\\mv_lease_owners_main.txt",'r')))
CompanyData = list(csv.reader(open("C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\test\\CompanyRawData\\mv_companies_active.txt",'r')))
BoreholeLeaseData = pd.DataFrame(WellLeaseData)   # converting text data to dataframe
CompanyLeaseData = pd.DataFrame(CompanyData)      # converting text data to dataframe  
leaseDatum = BoreholeLeaseData[0]                             #company leasedata column
mmsleaseData = BoreholeLeaseData[1]                           #company mmslease column
companyleaseDatum = CompanyLeaseData[0]                       #company identity
companyleaseNumber = CompanyLeaseData[2]                      #Company name data
companyAddress = CompanyLeaseData[3]                          #operator address
leaseNumber2 = []
mmsleaseNumber = []
operatorDatum = []


for leasedatum,leasenumbering in enumerate(leaseNumber1):
                  for leasedatum1,leasenumberingsearch in enumerate(leaseDatum):
                      if leasenumbering == leasenumberingsearch:
##                          print(leasenumberingsearch)
                          leaseNumber2.append(leasenumberingsearch)
                          for companyleasenumber,mmsleasenumber in enumerate(mmsleaseData):
                              if leasedatum1 == companyleasenumber:
##                                  print(mmsleasenumber)
                                  mmsleaseNumber.append(mmsleasenumber)
                                  for operatordetails,operatornumber in enumerate(companyleaseDatum):
                                      if mmsleasenumber == operatornumber:
##                                          print(operatornumber)
                                          for operatorlease,operatordata in enumerate(companyleaseNumber):
                                              if operatordetails == operatorlease:
                                                  print(operatordata)
                                                  operatorDatum.append(operatordata)
                                                  for operatordata1,operatoraddress in enumerate(companyAddress):
                                                      if operatorlease == operatordata1:
                                                          print(operatoraddress)



writer = pd.ExcelWriter("C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\calculations\\ActiveLease.xlsx")
Lease  = pd.DataFrame.from_dict({'BlockName':blockNaming,'BlockNumber':blockNumbering,'LeaseNumber':leaseNumber1,'CompanyName':companyNames,"Latitude":surfaceLatitude,"Longitude":surfaceLongitude})
Lease.to_excel(writer,sheet_name= "Lowertertiarywells", header=True, index=False)     # creating excel sheet saving company latitude and longitude details of wells


                          
                          



