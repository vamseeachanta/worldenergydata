#Data Source download from browser
import urllib.request

url = 'https://www.data.bsee.gov/Well/Borehole/Default.aspx'
response = urllib.request.urlopen(url)
#the code downloads the file contents into the variable data from http link
data = response.read()      
# a `str`; this step can't be used if data is binary
text = data.decode('utf-8')
print(text) 
print("Downloading Data is Finished but NOT WORKING")