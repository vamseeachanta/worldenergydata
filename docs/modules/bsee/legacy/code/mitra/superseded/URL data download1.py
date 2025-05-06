### -*- coding: utf-8 -*-
##"""
##Created on Thu Feb 15 17:24:37 2018
##
##@author: vamsee.achanta
##"""
##import datetime
##
##def createTimeStamp(programRunIntervalTime):
##    timeNow = datetime.datetime.now()
##    createdTimeMinute = int((timeNow.minute)/programRunIntervalTime)*programRunIntervalTime
##    createdTimeStamp = timeNow.replace(minute = createdTimeMinute, second =0, microsecond = 0)
##    return createdTimeStamp

from zipfile import ZipFile
from urllib.request import urlopen   
import pandas as pd
import csv
URL = "https://www.data.boem.gov/GGStudies/Files/2016%20Atlas%20Update.zip"
url = urlopen(URL)

dfs = {text_file.filename: pd.read_csv(zip_file.open(text_file.filename))
       for text_file in zip_file.infolist()
       if text_file.filename.endswith('.txt')}

