#!/usr/bin/python3

#   The sensors (or rather the suppoorting app) report
#   values for vpd , dew point and heat index
#   so I found the equations that provide these results.
#   mostly for fun.  One could of course just get them from
#   temp and humidity saved as raw data which would probably
#   make more sense than saving these extra peices
#
#   VPD in kPa derived from
#   Temp C and relative humidity
#   Test data:
#   t=16.63 rh=62.6 -> 0.71kPa vpd dp=9.31
#   t=4.44 rh=81.0  -> 0,15KPa vpd dp=1.56
#   (Read from the sensor app)

import math

#
#   vpd calculation is taken from a random internet post
#   which claims its from [The ASCE Standardized Reference
#   Evapotranspiration Equation] which at any rate
#   agrees with what the sensor/app reports.
#   Apart from 1000 in there to convert to Kilo Pascals


def vpd(t, rh):
    svp = 610.78 * math.exp((t / (t + 237.3)) * 17.2694)
    vpd = svp * (1.0 - (rh / 100.0)) / 1000.0
    return vpd


#   Dew point calculation


def dew(t, rh):
    #
    #   There are a choice of calculations for determining dew point
    #   of varying degrees of precision and complexity.
    #
    #   This calculation appears to agree with the thermoBeacon sensor
    #   and is from a Texas Instruments document for the HDC1xxx humidity
    #   sensor
    #   https://e2e.ti.com › cfs-file › __key › Dew-Point

    alpha = 17.271
    beta = 237.7

    term = (alpha * t) / (beta + t)
    rhterm = math.log(rh / 100.0)

    dp = beta * (rhterm + term) / (alpha - rhterm - term)

    return dp


#   Heat index


def heat_index(t, rh):

    #   Taken from:
    #   A new empirical model of the temperature-humidity index
    #   Carl Schoen
    #   Journal of applied Meteorology and climatology
    #   Volume 44 issue 9
    #   Which is a pleasant read and a jolly good peice of work that is a
    #   marked improvement over polynomial approximation over a more limited range.

    d = dew(t, rh)  # Have to look into if this is the dew point calculation
    # in the paper

    hi = t - 1.0799 * math.exp(0.03755 * t) * (1.0 - math.exp(0.0801 * (d - 14.0)))

    return hi
