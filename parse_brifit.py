#!/usr/bin/python3

#
# 	Take the raw data log
# 	and get date temp/humidity etc data by location
#

from datetime import datetime
from dateutil import parser, tz
import sys


# Get rid of stuff after the specified string if its in there


def cutstring(delimiter, record):
    if delimiter in record:
        record = record[: record.index(delimiter)]
    return record


def parse_measurement(DATE, record):
    datums = [DATE]

    delimiterStop = ")"
    delimiterStart = "("

    while True:
        if delimiterStart in record and delimiterStop in record:
            item = record[
                record.index(delimiterStart)
                + len(delimiterStart) : record.index(delimiterStop)
            ]
            record = record[record.index(delimiterStop) + len(delimiterStop) :]
            # item is now a string of location and data values
            datums.append(item)
        else:
            break

    return datums


def findlocs(locdata):
    locations = set()
    for point in locdata:
        DAT = point.pop(0)
        meas = point
        for item in meas:
            decomp = item.split(",")
            locations.add(decomp[0])
        # Reverse the effect of the pop
        point.insert(0, DAT)  # I should be working on a copy of the data but
    # not leaving it alone screws up. I lose the date info.
    # I don't understand that.

    #   NOTE: 'I should be working on a copy of the data' isn't how it works.
    #   Read https://nedbatchelder.com/text/names.html

    loc = list(locations)
    for index, bori in enumerate(loc):
        loc[index] = loc[index].replace("'", "")

    return sorted(loc)


def flttofixed(value):
    # Need numeric values in fixed width

    datum = value

    if datum is None:  # A problem
        fmt = "---"  # Sidestep it..
    else:
        datum = datum.strip()
        val = float(datum)
        val = round(val, 2)
        fmt = str(val)

    fmt = fmt.ljust(6)

    return fmt


def output(graph):
    for item in graph:
        when = item[0]  # When the values were measured

        #   Format depending on how many items we find
        #
        outstr = ""
        for number in range(len(item) - 1):
            if number == 0:
                outstr = outstr + flttofixed(item[number + 1])
            else:
                outstr = outstr + " ,  " + flttofixed(item[number + 1])

        print(when, outstr)


def usage():
    print("Usage: InputFile Parameter samples(last N)")
    print("Where Parameter codes are:\n")
    print(
        "temperature 1  humidity 2 vpd_point  3 dew_point  4 heat_index 5 Battery Voltage    6\n"
    )


parametermeanings = [
    "Temperature",
    "Humidity",
    "Vapour Pressure Deficit",
    "Dew_point",
    "Heat_index",
    "Battery Voltage",
]


#
#   Command line input and validation
#   Errors result in a usage hint and exit


def validateargs(headerOnly):
    caller = sys.argv.pop(0)
    inputargs = sys.argv

    if len(inputargs) != 3:
        usage()
        exit()

    filename = inputargs[0]
    parameterSTR = inputargs[1]
    items = inputargs[2]

    if not parameterSTR.isdigit():
        usage()
        exit()
    parameter = int(parameterSTR)

    if not items.isdigit():
        usage()
        exit()
    itemsRequired = int(items)

    if parameter < 1 or 6 < parameter:
        usage()
        exit()

    #   Survived running the gauntlet

    massagerawdata(filename, parameter, headerOnly, itemsRequired)


#
#   Input validation complete.
#

outputData = True


def massagerawdata(filename, dataItem, headerOnly, itemsRequired):
    resurrect = open(filename, "r")
    restored = resurrect.readlines()
    resurrect.close()

    dataset = []

    for measurement in restored:
        # Isolate the datestring by getting rid of everything that follows
        # a few choice phrases

        record = measurement

        if "No temperature data in scan" in record:
            continue

        record = cutstring("Signal", record)
        record = cutstring("Data:", record)
        record = cutstring("No thermometers found", record)

        # All that should be left is the date

        DATE = parser.parse(record)

        delimiter = "Data:"
        if delimiter in measurement:
            record = measurement
            record = record[record.index(delimiter) + len(delimiter) :]
            meas = parse_measurement(DATE, record)
            dataset.append(meas)

    locdata = dataset.copy()
    rawdata = list(dataset)

    loc = findlocs(locdata)  # Make output human friendly if possible

    datalist = []
    for point in rawdata:
        datapoint = [None] * (len(loc) + 1)
        datapoint[0] = point.pop(0)
        meas = point
        for oom in meas:
            decomp = oom.split(",")
            dblquot = decomp[0]
            dblquot = dblquot.replace("'", "")  # simplify double quote to single
            pos = loc.index(dblquot)
            datapoint[pos + 1] = decomp[dataItem]
        datalist.append(datapoint)

    print(parametermeanings[dataItem - 1], "at locations")
    print("\t\t", loc)

    if not headerOnly:
        itemsRequired = min(itemsRequired, len(datalist))
        output(datalist[-itemsRequired:])

    exit()


# 	The usual entry point stuff...

if __name__ == "__main__":
    validateargs(False)  # Both header and data are required
