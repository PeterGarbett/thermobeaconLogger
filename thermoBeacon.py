#!/usr/bin/python3
#
#   	Peter Garbett Jan 2023
#
#   	Get data from thermoBeacon bluetooth thermometers
#
# 	Scan data for a few minutes then trawl through
# 	to find items of interest and decode them.
# 	This mode of operation is suitable for batch operation
# 	expected to be operated via cron. If you want data fast
# 	this isn't for you. Log data to stdout.
#   This can then be processed at leisure. see parse_brifit.py
#
#
#  Gets raw data using bluetoothctl via pexpect
#  Then have to fish out ManufacturerData , decode it then
#  remove erronous records using range check on temperature
#  and checks on timestamps. The odd packet is arriving
#  with radically incorrect values.
#
#  bluetoothctl needs to be run with appropriate privs
#  running as root or preferably being in group lp works
#  You may well think alternatives are more to your liking

import pexpect
import time
import statistics
import pickle
import sys
import vpd_calc
from numpy import mean

#   Debugging facility: save and restore sensor data
#   replay and debug by loading it by changing flags
#   and files here.
#   Quick and reproducible


home_directory = "/home/peter/thermobeacon"

loadTestData = False
dataLoadFile = home_directory + "/rawBTdata.pk"
saveTestData = False
dataDumpFile = home_directory + "/rawBTdata.pk"

# Some failures get recorded without intervention or request

faildata = home_directory + "/tempfail.pk"


#   Define which controller to use.
#   Had to include a better v5 bluetooth dongle to read low power
#   bluetooth. Hence need to ensure this is the selected controller.
#   Here is its MAC (all data in upper case)
#   set to "" if you require the default, possibly only controller
#   since thats what bluetoothctl will use
#
# controllerMAC = ""
controllerMAC = "0E:12:34:4E:AB:20"
# controllerMAC = "8C:88:2B:67:23:CE"
# controllerMAC = "0E:12:34:4E:A6:C7"

#   The time needed on a scan to collect enough advertising packets
#   I've worked out experimentally.  Might be overkill
#
scantime = 300.0

#   I work out the thermoBeacon MAC's from the scan but one thing
#   I can't work out is where they are. This dictionary relates
#   MACs to location.  This degrades gracefully if an unknown MAC appears.
#   to just refferring to the device by it's MAC

MACLocations = {
    "1A:02:00:00:0D:03": "Outside",
    "1A:67:00:00:06:5C": "Kitchen",
    "BC:DA:00:00:04:27": "LivingRoom",
    "BE:25:00:00:0A:29": "Bedroom",
}

# Finished defining user dependent stuff

# Finding signal strengths is useful when placing devices
# but can then be suppressed

findRssi = False

# Data types in order they appear in the records, and the
# scaling factors to get to the stated units

titles = ["Volts", "temp C", "Humidity %", "Seconds"]
scaling = [1000.0, 16, 16, 1]

#
#   These are the range limits according to the advertising blurb
#

mintemp = -20.0
maxtemp = 65.0


#   Tidy up all sort of junk from the records


def tidy(record):

    nocrud = record.replace("\n", "")
    nocrud = nocrud.replace("\r", "")
    nocrud = nocrud.replace("\x1b", "")
    nocrud = nocrud.upper()

    # 	The most robust method appears to be to delete
    # 	whatever appears prior to the Device string
    # 	which seems to vary

    if "DEVICE" in nocrud:
        cutdown = nocrud[nocrud.index("DEVICE") :]
        return cutdown.upper()

    return nocrud


# Old fashioned way to map a function over a list...


def tidyList(records):
    for index, elem in enumerate(records):
        records[index] = tidy(records[index])


#   Spawn bluetoothctl and talk using utf-8
#   Tried a number of alternatives ; expect from bash, coproc etc.
#   python pexpect seems by far the most robust and understandable (by me at least).
#   Select controller , then start scan


def collect_data(controllerMAC):

    DeviceScan = []

    # 	Alternativly, if requested
    #   Load test data and return if required.
    #   This is fast and reproducible
    # for debugging

    if loadTestData:
        with open(dataLoadFile, "rb") as handle:
            DeviceScan = pickle.load(handle)
        handle.close()

        if [] == DeviceScan:
            print("Data collection failed\n")
            exit()

        return DeviceScan

    #
    #   Get data from device via bluetoothctl
    #   the try/expect catchs all sorts of failures
    #   such as timeout incorrect controller etc.
    #   these can be dealt with by the later code since
    #   you just get a null results list

    try:
        child = pexpect.spawn("bluetoothctl", encoding="utf-8", timeout=scantime)

        # 	uncommenting this line gives useful debug output for
        # 	monitoring progress of bluetoothctl

        # child.logfile = sys.stdout
        child.expect("Agent registered")
        result = child.readline()
        child.expect("#")
        if controllerMAC != "":
            child.send("select " + controllerMAC + "\n")
            result = child.readline()

        # 	select low power mode . we are looking for low power advertising packets

        child.send("menu scan\n")
        child.send("transport le\n")
        child.send("back\n")
        child.expect("#")

        #   Collect raw records making everything upper case to
        #   simplify searchs.

        timeout = scantime  # [seconds]
        timeout_start = time.time()

        child.send("scan on\n")

        while time.time() < timeout_start + timeout:
            result = child.readline()
            DeviceScan.append(result)

        #   Close down the child.
        #

        child.send("scan off\n")
        child.send("exit\n")
        child.expect("#")
        child.close()

    #   Catch all sorts of nonsense... wrong controller
    #   can't get hold of the dongle etc

    except:
        pass

    if [] == DeviceScan:
        print("Data collection failed\n")
        exit()

    # Store data (serialize) for later reload/run/debug

    if saveTestData:
        handle = open(dataLoadFile, "wb")
        pickle.dump(DeviceScan, handle)
        handle.close()

    return DeviceScan


#
#   Extract data from manufacturerData record
#   Note that when presented to this function
#   its been tided up considerably.


def interpret(elem, inspect):
    nocrud = elem
    text = nocrud.split()
    #   Resurrect what the MAC is from the reversed MAC in the record
    MAC = (
        text[5]
        + ":"
        + text[4]
        + ":"
        + text[3]
        + ":"
        + text[2]
        + ":"
        + text[1]
        + ":"
        + text[0]
    )
    datapoint = [0, 0, 0, 0, 0]

    #    MAC = MAC.replace(" ", "")
    datapoint[0] = MAC
    #
    #   Data is in pairs of hex bytes just after the reversed MAC
    #   in positions 0 to 5. Get the values converted to floats in a list

    startind = 6
    if inspect:
        print(text)
    for num in range(startind, 14, 2):
        # Data bytes are backwards in pairs
        data1 = text[num + 1] + text[num]
        if inspect:
            print(data1)
        typenum = int((num - startind) / 2)
        value = int(data1, base=16) / scaling[typenum]
        #  The above has misinterpreted bit at 2^11 as being +ve
        #  however its in 11 bit twos complement format
        #  whichs is fine if its zero. If we get to give a value equal to or above 2048
        #  That bit should have been counted as negative so correct it
        if 2048 <= value:
            value = value - 4096
        datapoint[typenum + 1] = value

    return datapoint


#
#   main thread...
#
#


def main():

    #
    #   Get raw data
    #

    DeviceScan = collect_data(controllerMAC)

    #   Tidy up all sort of junk from the records

    tidyList(DeviceScan)

    #   Find the MACs corresponding to the thermoBeacon
    #   The above loop means we search for UPPER case thermoBeacon
    #   and all thats left in these records is the MAC

    thermometers = []
    for index, elem in enumerate(DeviceScan):
        if "THERMOBEACON" in elem:
            nocrud = DeviceScan[index]
            nocrud = nocrud.replace(" ", "")
            nocrud = nocrud.replace("DEVICE", "")
            nocrud = nocrud.replace("THERMOBEACON", "")
            thermometers.append(nocrud)

    #   Remove duplicates

    thermometers = list(dict.fromkeys(thermometers))

    if [] == thermometers:
        print("No thermometers found\n")
        exit()

    #   Find rssi data for our thermometers

    thermometerRSSI = []

    #
    #   This logical supresses the RSSI logging since its of little
    #   use once satisfactory locations have been found for the devices

    if findRssi:

        #   Find RSSI records
        #   Save a list of MAC's and pwr levels

        for index, elem in enumerate(DeviceScan):
            record = tidy(elem)
            if "RSSI" in record:
                comp = record.split()

                # if its a MAC of interest i.e. belongs to a thermometer
                # save it away

                if comp[1] in thermometers:
                    # Save MAC and pwr level converted to integer
                    RSSI = (comp[1], int(comp[3]))
                    thermometerRSSI.append(RSSI)

        # Get a list of pwr levels for each thermometer MAC in turn

        rssi_stats = []
        for therm in thermometers:
            pwrs = []
            for pwr in thermometerRSSI:
                if therm == pwr[0]:
                    pwrs.append(pwr[1])

            # Now get min max and average RSSI for each MAC and save

            if pwrs != []:
                # convert from mac to easy recognised name if possible
                location = MACLocations.get(therm, therm)

                #   save mac and rssi stats

                pwrstats = (
                    location,
                    round(min(pwrs), 2),
                    round(mean(pwrs), 2),
                    round(max(pwrs), 2),
                )
                rssi_stats.append(pwrstats)

    #
    #   The manufacturer data record has in it the MAC
    #   reversed so we need to produce a list of these

    reversedMAC = []

    for mac in thermometers:
        decomp = mac.split(":")
        if len(decomp) == 6:
            rev = (
                decomp[5]
                + " "
                + decomp[4]
                + " "
                + decomp[3]
                + " "
                + decomp[2]
                + " "
                + decomp[1]
                + " "
                + decomp[0]
            )
            reversedMAC.append(rev)

    #
    #   Find records with reversed MAC's in them
    #   should also say manufacturerdata but this looks sufficient
    #   to identify them

    dataforMAC = []
    for ribit in reversedMAC:
        for elem in DeviceScan:
            #            print("A candidate record that may include a reversed MAC",elem)
            #            print("search it for",ribit)
            if ribit in elem:
                #                print("A record that includes a reversed MAC",elem)
                # Remove everything prior to the reversed MAC
                # This varies and is best eliminated

                cutdown = elem[elem.index(ribit) :]
                dataforMAC.append(cutdown)

    if [] == dataforMAC:
        print("No temperature data in scan\n")
        exit()
    #
    #   Now to interpret the data
    #

    datapoint = [0, 0, 0, 0, 0]

    datums = []

    for index, elem in enumerate(dataforMAC):
        nocrud = elem
        datapoint = interpret(nocrud, False)
        datums.append(datapoint)
    #
    #   Only range check implemented is on temperature
    #   could add humidity
    #   data order is MAC,battery Voltage,Temperature,humidity and time

    range_checked = []
    for elem in datums:
        if mintemp <= elem[2] <= maxtemp:
            range_checked.append(elem)

    if [] == range_checked:
        print("No data in range\n")
        exit()

    #
    #   Sanity check on the timer values
    #
    # Use a window centred on the median to exclude
    # outliers.  These tend to be way off.

    range_checked = sorted(range_checked)

    # Save all the counter values associated
    # with a given mac as  [mac,[counter values...]]

    timelist = []
    for therm in thermometers:
        timesr = []
        for dats in range_checked:
            if therm == dats[0]:
                timesr.append(dats[4])
        timelist.append([therm, timesr])

    #    print(timelist)
    # Now form statistics on the counter list
    # Save dictionary items mac -> bounds

    macrangelimits = {}
    for item in timelist:
        mac = item[0]
        times = item[1]
        if times != []:
            midpoint = statistics.median(times)
        else:
            midpoint = 0.0  # if no data the midpoint is arbitrary

        #   These are quite wide limits. one might expect scantime/2.0
        #   The behaviour of this code
        #   when the scantime changes would be .. interesting.

        lowerbnd = int(midpoint - scantime)
        upperbnd = int(midpoint + scantime)
        upperlimit = max(times)
        lowerlimit = min(times)
        macrangelimits.update({mac: (lowerbnd, upperbnd)})

    # Now (counter) range check the data in the temperature
    # range checked data in range_checked
    # if dats[4] in range(lowerbnd, upperbnd):

    validated = []
    for dats in range_checked:
        limits = macrangelimits.get(dats[0])
        if dats[4] in range(limits[0], limits[1]):
            validated.append(dats)

    if [] == validated:
        print("Data validation checks all fail\n")
        exit()

    #   data order is MAC,battery Voltage,Temperature,humidity and time
    #   Find average readings

    results = []
    for mack in thermometers:
        #       Convert MAC to more human friendly reference
        location = MACLocations.get(mack, mack)

        # Take averages for battery voltage temperature and humidity
        # first, zero counters, sum items and count occurrences

        pwr = 0.0
        temp = 0.0
        humid = 0.0
        items = 0.0

        for elem in validated:
            if mack in elem[0]:
                pwr += elem[1]
                temp += elem[2]
                humid += elem[3]
                items += 1.0

        #   if no data provide obviously incorrect data
        #   want to have same output format as usual
        failed = False
        if items == 0.0:
            failed = True
            results.append((location, 0.0, -273.15, 100.0, -1, -1, -1))
        else:
            # Form averages
            pwr = pwr / items
            temp = temp / items
            humid = humid / items
            # from which we determine these
            vpd_point = vpd_calc.vpd(temp, humid)
            dew_point = vpd_calc.dew(temp, humid)
            heat_index = vpd_calc.heat_index(temp, humid)

            # 	save results to two dp

            results.append(
                (
                    location,
                    round(temp, 2),
                    round(humid, 2),
                    round(vpd_point, 2),
                    round(dew_point, 2),
                    round(heat_index, 2),
                    round(pwr, 2),
                )
            )

    if failed:
        handle = open(faildata, "wb")
        pickle.dump(DeviceScan, handle)
        handle.close()

    #   If asked to find signal strengths

    if findRssi:
        # and actually found some, report the results
        if rssi_stats != []:
            print("Signal strength:", sorted(rssi_stats))

    #  for each sensor report
    # Sensor,temperature,humidity,vpd,dew pt,heat index,Battery voltage

    print("Data:", sorted(results))


# 	The usual entry point stuff...

if __name__ == "__main__":
    main()
