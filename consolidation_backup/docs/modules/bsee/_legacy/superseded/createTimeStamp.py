### -*- coding: utf-8 -*-
##"""
##Created on Thu Feb 15 17:24:37 2018
##
##@author: vamsee.achanta
##"""
import datetime


def createTimeStamp(programRunIntervalTime):
    timeNow = datetime.datetime.now()
    createdTimeMinute = int((timeNow.minute)/programRunIntervalTime)*programRunIntervalTime
    createdTimeStamp = timeNow.replace(minute = createdTimeMinute, second =0, microsecond = 0)
    return createdTimeStamp
