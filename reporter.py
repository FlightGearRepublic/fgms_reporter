import pickle
import configparser
import telnetlib
import math
import csv
from time import time
from time import sleep

delay = 15

debug = 1 # use this to turn a bunch of print statements on or off.

# make sure the config file exists.
try:
    _ = open("config.ini","rt")
except FileNotFoundError as e:
    _ = open("config.ini","xt")
    print("[general]\ncallsigns=pinto|PINTO|Leto|USAF001\naircraft=JA37-Viggen|AJ37-Viggen|AJS37-Viggen|F-15C\nservers=mpserver01.flightgear.org",file=_)
    print("config.ini not found, creating default config.ini...")
finally:
    _.close()
    
# make sure the csv file exists
try:
    _ = open("output.csv","rt")
except FileNotFoundError as e:
    _ = open("output.csv","xt")
    # parr[cs] = {'active':0,'lastmodel':"",'x':0,'y':0,'z':0,'lat':0,'lon':0,'time':0,'model':{}}
    print("callsign,model,eft",file=_)
    print("output.csv not found, creating default output.csv...")
finally:
    _.close

# make sure the pickle database exists
try:
    _ = open("db.pickle","rb")
except FileNotFoundError as e:
    _ = open("db.pickle","xb")
    pickle.dump({},_)
    print("db.pickle not found, creating default db.pickle...")
finally:
    _.close()
    
# main loop
def loop():
    if debug == 1:
        print("beginning main loop")
    #config stuff
    conf = configparser.ConfigParser()
    conf.read('config.ini')
    callsigns = str(conf.get('general','callsigns')).split('|')
    aircraft = str(conf.get('general','aircraft')).split('|')
    servers = str(conf.get('general','servers')).split('|')
    
    #database stuff
    pickle_file = open('db.pickle','rb')
    parr = pickle.load(pickle_file)
    pickle_file.close()
    if parr == None:
        parr = {}
        
    #telnet stuff - aggregate our data.
    data = ""
    for server in servers:
        tn = telnetlib.Telnet(server,5001)
        data = data + str(tn.read_all())
        tn.close()
    data = data.split('\\n')
    
    # make sure we have everybody in parr.
    for cs in callsigns:
        if not cs in parr:
            parr[cs] = {'active':0,'lastmodel':"",'x':0,'y':0,'z':0,'time':0,'model':{}}
        for ac in aircraft:
            if not ac in parr[cs]['model']:
                parr[cs]['model'][ac] = 0
        found = 0
        for d in data:
            if d.find('@') != -1 and d.split('@')[0] == cs:
                found = 1
                if debug == 1:
                    print("found " + cs + " online.")
                extract = d.split('@')[1].split(' ')
                model = extract[10].split('/')[-1].split('.xml')[0]
                if model in parr[cs]['model']:
                    if ( parr[cs]['active'] == 0 ) or ( parr[cs]['active'] == 1 and parr[cs]['lastmodel'] != model ) :
                        if debug == 1:
                            print(cs + " was not online or the model changed. setting up...")
                        parr[cs]['lastmodel'] = model
                        parr[cs]['time'] = time()
                        parr[cs]['x'] = float(extract[1])
                        parr[cs]['y'] = float(extract[2])
                        parr[cs]['z'] = float(extract[3])
                    elif parr[cs]['active'] == 1 and parr[cs]['lastmodel'] == model:
                        # active - we need to calculate speed to see if we should add to eft.
                        x1 = float(extract[1])
                        y1 = float(extract[2])
                        z1 = float(extract[3])
                        x2 = parr[cs]['x']
                        y2 = parr[cs]['y']
                        z2 = parr[cs]['z']
                        distance = math.sqrt( (z2 - z1) ** 2 + (x2 - x1) ** 2 + (y2 - y1) ** 2)
                        update_time = time() - parr[cs]['time']
                        speed = distance / update_time # in meters/second
                        if speed > 2.57: #i.e. 5 knots
                            parr[cs]['model'][model] = parr[cs]['model'][model] + update_time
                            if debug == 1:
                                print(cs + " is moving at " + str(speed) + " m/s, adding " + str(update_time) + " to " + model)
                        elif debug == 1:
                            print(cs + " has not moved more than 5kts.")
                        parr[cs]['time'] = time()
                        parr[cs]['x'] = x1
                        parr[cs]['y'] = y1
                        parr[cs]['z'] = z1
        parr[cs]['active'] = found

    # now need to export parr to csv and to pickle DB.
    pickle_file = open('db.pickle','wb')
    pickle.dump(parr,pickle_file)
    pickle_file.close()
    
    csv_file = open('output.csv','wt')
    try:
        writer = csv.writer(csv_file)
        writer.writerow(('callsign','model','eft'))
        for cs in parr:
            for model in parr[cs]['model']:
                writer.writerow((cs,model,parr[cs]['model'][model]))
    finally:
        csv_file.close()
    
    # wait -delay- seconds and run 'er again!
    sleep(delay)
    loop()
    
loop()