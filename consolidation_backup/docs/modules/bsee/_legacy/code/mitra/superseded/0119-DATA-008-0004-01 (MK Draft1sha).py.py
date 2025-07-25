import ogr,csv,sys

shpfile=r"C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\test\\blocks.shp" #sys.argv[1]
csvfile=r'C:\\Users\\AceEngineer-04\\Dropbox\\0119 Programming\\008 GoM Wells\\CODE\\test\\blocks.csv' #sys.argv[2]

#Open files
csvfile=open(csvfile,'w')
ds=ogr.Open(shpfile)
lyr=ds.GetLayer()

#Get field names
dfn=lyr.GetLayerDefn()
nfields=dfn.GetFieldCount()
fields=[]
for i in range(nfields):
    fields.append(dfn.GetFieldDefn(i).GetName())
fields.append('kmlgeometry')
csvwriter = csv.DictWriter(csvfile, fields)
try:
    csvwriter.writeheader()
except:
    csvfile.write(','.join(fields)+'\n')
        

# Write attributes and kml out to csv
for feat in lyr:
    attributes=feat.items()
    geom=feat.GetGeometryRef()
    attributes['kmlgeometry']=geom.ExportToKML()
    csvwriter.writerow(attributes)

#clean up
del csvwriter,lyr,ds
csvfile.close()
