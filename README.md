Simple python3 scripts to capture and log/inspect brifit ble thermobeacon data.

I obtained some Brifit Thermometer Hygrometers 
which transmit their data via low energy Bluetooth
advertising packets.

I wanted to access the information remotely so I
wrote code to log and inspect the logged data on my Linux
machine running Fedora 35. What exising solutions I could find
involved hcitool which is deprecated and I also wanted to be standalone
rather than get involved with home automation . python is a 
good fit to the post processing and pexpect was easier to get
working than the alternatives I tried.

I used pexpect and bluetoothctl to directly capture
data. The sensors advertise themselves as thermobeacons.
You need appropriate privs for bluetoothctl e.g. in  group lp

The code does a scan and then we inspect results which is
appropriate for running as a batch job which I do every half hour.

I also include results for Vapour Pressure Deficit,Dew point and
Heat index since the app for the devices give you this. Might 
have been more sensible to leave this to post processing
since these items are derived entirely from temperature and
humidity.  

I include some error checking since I get occasional rogue results.
These are a temperature check which the sensor claims should
be -20 to 65 degrees C and a check on the counters which
should be in a range commensurate with the sampling time (each 
sensor has a separate counter which I believe I inspect individually,
though I haven't tested what happens if they diverge)

There are a few site dependent constants to set up at the start
of the code in thermobeacon.py, such as controller MAC and sensor locations
and also the log file location which is on my home directory. You may have other ideas.
RSSI value logging can be enabled/disabled.


README			This file
temps			Display latest logged humidity values for temperature
humids			Display latest logged humidity values for humidity
LogTemp			Script to run from crontab
logBaT			Run thermobeacon data collection (called from logTemp)
parse_brifit.py		Parse the raw data log and extract required data
thermoBeacon.py		Data colection via Bluetooth 
vpd_calc.py		VPD dew point and Heat index calculations


temps script sample output

Temperature at locations
		 ['Bedroom', 'Kitchen', 'LivingRoom', 'Outside']
2023-01-26 17:05:03+00:00 ,19.88 ,13.38 ,17.26 ,6.3   

thermobeacon.py sample output.
Tuples are (Sensor,temperature,humidity,vpd,dew pt,heat index,Battery voltage)

Thu 26 Jan 17:05:03 GMT 2023 Data: [('Bedroom', 19.88, 45.44, 1.27, 7.73, 18.98, 2.92), ('Kitchen', 13.38, 57.75, 0.65, 5.22, 12.47, 2.97), ('LivingRoom', 17.26, 45.71, 1.07, 5.44, 16.23, 2.95), ('Outside', 6.3, 34.94, 0.62, -8.05, 5.17, 2.95)]



