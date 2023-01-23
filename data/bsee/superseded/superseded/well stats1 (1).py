import csv

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd
import pylab

plt.style.use("ggplot")
df = pd.read_csv('C:\\Users\\AceEngineer-04\\Desktop\\Mithra_W\\reallife\\csv files\\Borehole (2).csv')
for row in df:
    if row == 'Company Name':
        
        x = 'Chevron U.S.A. Inc.'
        y =  df[df[row] == x][row].count()
        x1 = 'Exxon Mobil Corporation'
        y1 = df[df[row] == x1][row].count()
        x2 = 'Northstar Offshore Group, LLC'
        y2 = df[df[row] == x2][row].count()
        x3 = 'Stone Energy Corporation'
        y3 = df[df[row] == x3][row].count()
        x4 = 'Magnolia Petroleum Company'
        y4 = df[df[row] == x4][row].count()
        x5 = 'Fieldwood Energy LLC'
        y5 = df[df[row] == x5][row].count()
        x6 = 'McMoRan Oil & Gas LLC'
        y6 = df[df[row] == x6][row].count()
        x7 = 'BP Alaska Exploration Inc.'
        y7 = df[df[row] == x7][row].count()
        x8 = 'MOBIL OIL EXPLORATION & PRODUCING SOUTHEAST INC.'
        y8 = df[df[row] == x8][row].count()
        x9 = 'BP America Production Company'
        y9 = df[df[row] == x9][row].count()
        x10 = 'Apache Corporation'
        y10 = df[df[row] == x10][row].count()
        x11 = 'Union Oil Company of California'
        y11 = df[df[row] == x11][row].count()
        x12 = 'Sun Oil Company'
        y12 = df[df[row] == x12][row].count()
        x13 = 'Kerr-McGee Corporation'
        y13 =  df[df[row] == x13][row].count()
        x14 = 'Cabot Corporation'
        y14 = df[df[row] == x14][row].count()
        x15 = 'The Louisiana Land and Exploration Company'
        y15 = df[df[row] == x15][row].count()
        x16 = 'Tenneco Oil Company'
        y16 = df[df[row] == x16][row].count()
        x17 = 'Gordon Street, Inc.'
        y17 = df[df[row] == x17][row].count()
        x18 = 'American Exploration Company'
        y18 = df[df[row] == x18][row].count()
        x19 = 'Mariner Energy, Inc.'
        y19 = df[df[row] == x19][row].count()
        x20 = 'The Pure Oil Company'
        y20 = df[df[row] == x20][row].count()
        x21 = 'Tengasco, Inc.'
        y21 = df[df[row] == x21][row].count()
        x22 = 'The Superior Oil Company'
        y22 = df[df[row] == x22][row].count()
        x23 = 'Merit Energy Company, LLC'
        y23 = df[df[row] == x23][row].count()
        x24 = 'EP Energy E&P Company, L.P.'
        y24 = df[df[row] == x24][row].count()
        x25 = 'Energy XXI GOM, LLC'
        y25 = df[df[row] == x25][row].count()
        x26 = 'El Paso Production Company'
        y26 = df[df[row] == x26][row].count()
        x27 = 'W & T Offshore, Inc.'
        y27 = df[df[row] == x27][row].count()
        x28 = 'Sabine Oil & Gas Corporation'
        y28 = df[df[row] == x28][row].count()
        x29 = 'Conoco Inc.'
        y29 = df[df[row] == x29][row].count()
        x30 = 'McMoRan Oil & Gas LLC'
        y30 = df[df[row] == x30][row].count()
        x31 = 'Eni US Operating Co. Inc.'
        y31 = df[df[row] == x31][row].count()
        x32 = 'Seneca Resources Corporation'
        y32 = df[df[row] == x32][row].count()
        x33 = 'Shell Oil Company'
        y33 =  df[df[row] == x33][row].count()
        x34 = 'Gulf Oil Corporation'
        y34 =  df[df[row] == x34][row].count()
        x35 = 'Humble Oil & Refining Company'
        y35 =  df[df[row] == x35][row].count()
        x36 = 'Midcon Offshore, Inc.'
        y36 = df[df[row] == x36][row].count()
        x37 = 'Tarpon Operating & Development, L.L.C.'
        y37 = df[df[row] == x37][row].count()
        x38 = 'Cox Operating, L.L.C.'
        y38 = df[df[row] == x38][row].count()
        x39 = 'General American Oil Company of Texas'
        y39 = df[df[row] == x39][row].count()
        x40 = 'Westport Resources Corporation'
        y40 = df[df[row] == x40][row].count()
        x41 = 'Conn Energy, Inc.'
        y41 = df[df[row] == x41][row].count()
        x42 = 'Newfield Exploration Company'
        y42 = df[df[row] == x42][row].count()
        x43 = 'Energy Resource Technology, Inc.'
        y43 = df[df[row] == x43][row].count()
        x44 = 'Ocean Drilling & Exploration Company'
        y44 = df[df[row] == x44][row].count()
        x45 = 'Black Elk Energy Offshore Operations, LLC'
        y45 = df[df[row] == x45][row].count()
        x46 = 'Offshore Shelf LLC'
        y46 = df[df[row] == x46][row].count()
        x47 = 'Texaco Inc.'
        y47 = df[df[row] == x47][row].count()
        x48 = 'General Atlantic Resources, Inc.'
        y48 = df[df[row] == x48][row].count()
        x49 = 'Senior - G & A Operating Company, Inc.'
        y49 = df[df[row] == x49][row].count()
        x50 = 'Murphy Exploration & Production Company'
        y50 = df[df[row] == x50][row].count()
        x51 = 'ATP Oil & Gas Corporation'
        y51 = df[df[row] == x51][row].count()
        x52 = 'Sojitz Energy Venture, Inc.'
        y52 = df[df[row] == x52][row].count()
        x53 = 'TDC Energy LLC'
        y53 = df[df[row] == x53][row].count()
        x54 = 'Gulfstream Resources, Inc.'
        y54 = df[df[row] == x54][row].count()
        x55 = 'Homestake Sulphur Company'
        y55 = df[df[row] == x55][row].count()
        x56 = 'C & K Offshore Company'
        y56 = df[df[row] == x56][row].count()
        x57 = 'Enron Corp.'
        y57 = df[df[row] == x57][row].count()
        x58 = 'J. M. Huber Corporation'
        y58 = df[df[row] == x58][row].count()
        x59 = 'Diamond Shamrock Offshore Partners Limited Partnership'
        y59 = df[df[row] == x59][row].count()
        x60 = 'Transco Exploration Company'
        y60 = df[df[row] == x60][row].count()
        x61 = 'Samedan Oil Corporation'
        y61 = df[df[row] == x61][row].count()
        x62 = 'Devon Energy Production Co., L.P.'
        y62 = df[df[row] == x62][row].count()
        x63 = 'Hamilton Brothers Oil Company'
        y63 = df[df[row] == x63][row].count()
        x64 =' Tomlinson Offshore, Inc.'
        y64 = df[df[row] == x64][row].count()
        x65 = 'Placid Oil Company'
        y65 = df[df[row] == x65][row].count()
        x66 = 'Allied Natural Gas Corporation'
        y66 = df[df[row] == x66][row].count()
        x67 = 'Noble Energy, Inc.'
        y67 = df[df[row] == x67][row].count()
        x68 = 'Forcenergy Inc'
        y68 = df[df[row] == x68][row].count()
        x69 = 'Elf Aquitaine, Inc.'
        y69 = df[df[row] == x69][row].count()
        x70 = 'TOTAL E&P USA, INC.'
        y70 = df[df[row] == x70][row].count()
        x71 = 'Four Star Oil & Gas Company'
        y71 = df[df[row] == x71][row].count()
        x72 = 'BelNorth Petroleum Corporation'
        y72 = df[df[row] == x72][row].count()
        x73 = 'Odeco Oil & Gas Company'
        y73 =  df[df[row] == x73][row].count()
        x74 = 'Union Texas Petroleum Corporation'
        y74 =  df[df[row] == x74][row].count()
        x75 = 'Pogo Producing Company'
        y75 =  df[df[row] == x75][row].count()
        x76 = 'Occidental Petroleum Corporation'
        y76 = df[df[row] == x76][row].count()
        x77 = 'BHP Petroleum Company Inc.'
        y77 = df[df[row] == x77][row].count()
        x78 = 'ORYX ENERGY COMPANY'
        y78 = df[df[row] == x78][row].count()
        x79 = 'Zapata Exploration Company'
        y79 = df[df[row] == x79][row].count()
        x80 = 'PennzEnergy Company'
        y80 = df[df[row] == x80][row].count()
        x81 = 'Hall-Houston Oil Company'
        y81 = df[df[row] == x81][row].count()
        x82 = 'Mobil Producing Texas & New Mexico Inc.'
        y82 = df[df[row] == x82][row].count()
        x83 = 'Mark Producing, Inc.'
        y83 = df[df[row] == x83][row].count()
        x84 = 'OXY USA Inc.'
        y84 = df[df[row] == x84][row].count()
        x85 = 'FMP Operating Company, a Limited Partnership'
        y85 = df[df[row] == x85][row].count()
        x86 = 'Freeport Minerals Company'
        y86 = df[df[row] == x86][row].count()
        x87 = 'Humble Oil & Refining Company'
        y87 = df[df[row] == x87][row].count()
        x88 = 'BP Exploration & Oil Inc.'
        y88 = df[df[row] == x88][row].count()
        x89 = 'Santa Fe International Corporation'
        y89 = df[df[row] == x89][row].count()
        x90 = 'Wayman W. Buchanan, Inc.'
        y90 = df[df[row] == x90][row].count()
        x91 = 'Texaco Exploration and Production, Inc.'
        y91 = df[df[row] == x91][row].count()
        x92 = 'Walter Oil & Gas Corporation'
        y92 = df[df[row] == x92][row].count()
        x93 = 'Pioneer Natural Resources USA, Inc.'
        y93 = df[df[row] == x93][row].count()
        x94 = 'Cities Service Oil Company'
        y94 = df[df[row] == x94][row].count()
        x95 = 'LLOG Exploration & Production Company, L.L.C.'
        y95 = df[df[row] == x95][row].count()
        x96 = 'Cockrell Oil Corporation'
        y96 = df[df[row] == x96][row].count()
        x97 = 'Peregrine Oil & Gas, LP'
        y97 = df[df[row] == x97][row].count()
        x98 = 'MC Offshore Petroleum, LLC'
        y98 = df[df[row] == x98][row].count()
        x99 = 'Skelly Oil Company'
        y99 = df[df[row] == x99][row].count()
        x100 = 'Rooster Petroleum, LLC'
        y100 = df[df[row] == x100][row].count()
        x111 = [x,x1,x2,x3,x4,x5,x6,x7,x8,x9,x10,x11,x12,x13,x14,x15,x16,x17,x18,x19,x20,x21,x22,x23,x24,x25,x26,x27,x28,x29,x30,x31,x32,x33,x34,x35,x36,x37,x38,
              x39,x40,x41,x42,x43,x44,x45,x46,x47,x48,x49,x50,]
        y111 = [y,y1,y2,y3,y4,y5,y6,y7,y8,y9,y10,y11,y12,y13,y14,y15,y16,y17,y18,y19,y20,y21,y22,y23,y24,y25,y26,y27,y28,y29,y30,y31,y32,y33,y34,y35,y36,y37,y38,
              y39,y40,y41,y42,y43,y44,y45,y46,y47,y48,y49,y50,]
        x112 = [x51,x52,x53,x54,x55,x56,x57,x58,x59,x60,x61,x62,x63,x64,x65,x66,x67,x68,x69,x70,x71,x72,x73,x74,x75,x76,x77,x78,
              x79,x80,x81,x82,x83,x84,x85,x86,x87,x88,x89,x90,x91,x92,x93,x94,x95,x96,x97,x98,x99,x100]
        y112 = [y51,y52,y53,y54,y55,y56,y57,y58,y59,y60,y61,y62,
              y63,y64,y65,y66,y67,y68,y69,y70,y71,y72,y73,y74,y75,y76,y77,y78,y79,y80,y81,y82,y83,y84,y85,y86,y87,y88,
              y89,y90,y91,y92,y93,y94,y95,y96,y97,y98,y99,y100]
        xy = ("\n".join(map(str, x111)))
        yx = ("\n".join(map(str, y111)))
        xy1 = ("\n".join(map(str, x112)))
        yx1 = ("\n".join(map(str, y112)))
        xx = range(51)
        xx1 = range(50)
        box = dict(facecolor='Blue', pad=5, alpha=0.20)
        fig = plt.figure()
        
        ax1=fig.add_subplot(111)
        ax1.set_title('Well Strategy')
        ax1.set_xlabel('COMPANY NAME', bbox=box)
        ax1.set_ylabel('WELLS OWNED', bbox=box)
        pylab.xticks(xx,x111, rotation=90)
        ax1.bar(xx,y111,width=0.5,color="b")


        
        plt.savefig('well STATS',dpi=800)
        plt.show()
