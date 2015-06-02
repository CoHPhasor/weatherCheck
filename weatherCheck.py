################################################################
#
#   ******** weatherCheck *********
#
#   This is a tool meant to retrieve current, forecast, and 7-day historical weather based on user input.
#       This tool uses the Weather Underground API, thanks to all the meteorologists!
#       www.wunderground.com
#
#       Additional thanks to Kevin and Q, thank you for your support and resources.  :-)
#
# Copyright 2015 Shaun Potts
################################################################

import requests
import json
import datetime
import getpass
from   datetime import date, timedelta
import sys
import argparse
import logging


#-----------------------------------------------------------------------
# Globals
#-----------------------------------------------------------------------

#   Setting up human readable exit codes
EXIT_STATUS_OK         = 0
EXIT_STATUS_ERROR      = 1

# Getting date
THIS_DAY = date.today()

#   Getting USER_NAME
USER_NAME = getpass.getuser()

#   Number of days to pull down from Weather Underground (Cold have a CLI flag to change this)
#       NOTE:  Weather Underground.com limits you to 10 calls/min, a cache needs to be utilized
DAYS_2_GET_HISTORICALS = 7

#   Setting up Weather Underground URL
WU_URL = 'http://api.wunderground.com/api/'

#   This is my API key, but could be swapped via CLI if we wanted another user
API_KEY = '5f348904b60ca855/'

#   When looking for historicals this can be used for the URL
TIME_FRAME = 'history_'

#   Static preferred temp for "A good day to get out"
PREF_TEMP = 68

#   Static preferred condition for "A good day to get out"
PREF_COND = 'Partly Cloudy'

#   Temporary location used for testing
#       NOTE: This can also be a zipcode '/q/94541.json' , I verified it pulled the same station KHWD
#               IF the zipcode can be verified it's no problem to run it.
LOCATION_QUERY = '/q/CA/San Jose'

#   This var will allow for us to switch out data types from json if desired
URL_EXTENSION = '.json'

#   Temporary flag tossed for testing (Output should be human readable or json by request)
OUTPUT_JSON = False
OUTPUT_AVG_HIST_7_DAY_TOTAL   = False
OUTPUT_AVG_HIST_7_DAY_BY_DAY  = False

OUTPUT_CURRENT_TEMP           = False
OUTPUT_GOOD_DAY               = False
OUTPUT_THREE_DAY_FORECAST     = False


###################################################################
#           TODO:
#                   -apiPoll: setup a list or dict of lists capable arg for poaching more than a single value from returns
#
#                   -historyLookup: As requested, this script will deliver the *last 7 days' mean temp from San Jose CA*
#                                    To be more useful and robust I could allow a user input for the date/zipcode for which to look passed.
#                                    ie; A user inputs 20140323 and gets mean temp data from between 20140316 20140322
#                                           Some provisions are in place that could allow these changes and would just take more time.   
#
#                   -A CACHE would be a good idea, be it in a temp dir, or a REDIS/et al database. Weather Underground's API call
#                       limit is easy to hit. (Not necessarily the 500/day, but the 10/min is easy as EACH day in the 7-day-call is singular)
#
#                   -Arg parsing, thoroughly validating commandline args is preferred and could be setup
#
#                   -Add arg to give city/state optionally vs zipcode as a creature-comfort
#
#                   -Setup defs to handle multiple requests to a call in list format to allow a cleaner, less global var dependant script
#                           (Meshes with arg parse overhaul)
#
#                   -Logging:  This is a fairly straightforward script and logging is not implemented.
#                              Some interesting things can be added in and the script will quickly gain complexity.
#                              Time could be spent in the future to add clear, concise logging to a file or even syslog
#
###################################################################





#-----------------------------------------------------------------------------
def historyLookup(start_date, days_2_go_back, wu_key, location):
    #   This def gathers historical data going back 'x' days from start_date
    
    #   Testing args to ensure we have what we need
    if not isinstance(start_date, date):
        print("Error: improper date format. Got %s of type %s" % start_date, type(start_date))
        sys.exit(EXIT_STATUS_ERROR)
        
    if not isinstance(days_2_go_back, int):
        print("Error: days_2_go_back is expected to be a whole number. Got %s of type %s" % (days_2_go_back, type(days_2_go_back)))
        sys.exit(EXIT_STATUS_ERROR)
        
    if not isinstance(wu_key, str):
        print("Error: wu_key (API key) is expected to be a string. Got: %s of type %s" % (wu_key, type(wu_key)))
        sys.exit(EXIT_STATUS_ERROR)        
    
    if not isinstance(location, str):
        print("Error: location provided must be a string. Got: %s of type %s" % (location, type(location)))
        sys.exit(EXIT_STATUS_ERROR)

    # Setting up counter which we'll use to start our lookup on the furthest days
    date_countdown = days_2_go_back
    
    # Creating an empty Dict to store each day's polled data
    hist_dict = dict()
    
    #   Looping through the date range to grab weather for the previous 7 days
    for i in range(1, (days_2_go_back + 1)):
        #   Initializing meantempi holder
        p_data = 0 
    
        #   setting timedelta each time we loop to grab another day
        d = start_date - timedelta(days=date_countdown)
        assembled_date = '%s%s%s' % (d.year, d.strftime('%m'), d.strftime('%d'))

    
        query_string = '%s%s%s%s%s%s' % (WU_URL, wu_key, TIME_FRAME, assembled_date, location, URL_EXTENSION)

        
        #   Running the query to Weather Underground and pulling the mean temp
        p_data = int(apiPoll(query_string)['history']['dailysummary'][0]['meantempi'])
        
        #   Adding this date's mean temp to the dir
        hist_dict.update({'%s' % assembled_date : p_data})
        #   Decrementing our counter to poll the next date closer to start_date
        date_countdown = date_countdown - 1
        
        
    return hist_dict
    
#----------------------------------------------------------------    
def apiPoll(assembled_query):
        #   TODO: Adjust this def to accept a list, or possibly a dict of things to pull from retrieved data
        #            instead of a full json dump

    #   This def assembles an http call for json data from Weather Underground
    #   We assume the WU_URL global var is the canonical source for the API's URL
    
    # Assuring the assembled_query is a string
    if not isinstance(assembled_query, str):
        print("Error: apiPoll must be given a string, got: %s of type %s" % (assembled_query, type(assembled_query)))
        sys.exit(EXIT_STATUS_ERROR)
        
    
    r = requests.get(assembled_query)
    data = r.json()

    #   Testing return to ensure that it doesn't contain an 'error' key. (The operation DOES NOT fail and responds with 200 anyway)
    if 'error' in data['response']:
        print("\n   Error retrieving weather: %s" % data['response']['error']['description'])
        sys.exit(EXIT_STATUS_ERROR)

    return data        
    
    
#----------------------------------------------------------------

def lookAtHistory():
    #   This def handles historical requests from the user, 
    #       including 7-day overall meant temp of an area, per day, and a json holding the data

    #   Future possibility: Checking to see if json output is requested, if so, push results out to return
        
    if OUTPUT_JSON:
        lookup_hist = historyLookup(THIS_DAY, DAYS_2_GET_HISTORICALS, API_KEY, LOCATION_QUERY)
        return lookup_hist
    
    #   If the user is solely looking for CLI printed results:
    elif OUTPUT_AVG_HIST_7_DAY_TOTAL or OUTPUT_AVG_HIST_7_DAY_BY_DAY:
    
        # Calling data from the API only once to keep our api key from getting locked out, then parsing differently for each call.
        lookup_hist = historyLookup(THIS_DAY, DAYS_2_GET_HISTORICALS, API_KEY, LOCATION_QUERY)

        
        if OUTPUT_AVG_HIST_7_DAY_TOTAL:
            weekly_avg = sum(lookup_hist.values()) / len(lookup_hist.values())
            print("\n   The average temperature of %s was %0d F over the last 7 days." % (LOCATION_QUERY, weekly_avg))
                
                
        if OUTPUT_AVG_HIST_7_DAY_BY_DAY:
            print("\n   The average temperature for the last 7 days is as follows:\n")
            for key, value in lookup_hist.items():
                print("Average Temperature for %s was %sF" % (key, value))
        
        #   If we got this far without outputting it's time to fail
    else:
        print("Error: We hit the lookAtHistory function but no output flag was matched")
        sys.exit(EXIT_STATUS_ERROR)
            
#----------------------------------------------------------------------------

def currentTemp(given_zip):
    #   This def pulls current weather data for a given zipcode
    
# http://api.wunderground.com/api/5f348904b60ca855/conditions/q/94541.json    
    lookup_curr_query = "%s%sconditions/q/%s%s" % (WU_URL, API_KEY, given_zip, URL_EXTENSION)
    
    #   Pulling current data from Weather Underground
    try:
        polled_current_weather = apiPoll(lookup_curr_query)
    
        #   Checking to see what data is actually required 
        #       (Looking forward, if there are calls for more pieces of data we can get away with flagging them and polling only once)
        if OUTPUT_CURRENT_TEMP:
        
            curr_temp = polled_current_weather['current_observation']['temp_f']
            
            #   This is currently checking a global boolean variable called OUTPUT_JSON
            #       It is a placeholder for the possibility of returning json as a switch at the commandline.
            if not OUTPUT_JSON:
                print("\n   The current temperature is %0d F in %s" % (curr_temp, given_zip))
                
            #   If OUTPUT_JSON is set return the raw data
            else:
                return curr_temp
            
            #   Failing to get the current temp data should drop us out and tell us
    except Exception as e:
        print("Error: %s", e )
        sys.exit(EXIT_STATUS_ERROR)

    
#----------------------------------------------------------------------------

def forecastWeather(given_zip):
    #   This def takes a user-input zipcode and a switch for either 3-day or "a good day to get out"
    #       (Future additions may include different preferences for "A good day to get out")
    
    # Making a legend of keys to ease the use of super-long lines ahead
    fC  = 'forecast'
    sFc = 'simpleforecast'
    fCd = 'forecastday'
    fH  = 'fahrenheit'
    hG  = 'high'
    cD  = 'conditions'
    wD  = 'weekday'
    mN  = 'monthname'
    
    lookup_curr_query = "%s%sforecast/q/%s%s" % (WU_URL, API_KEY, given_zip, URL_EXTENSION)
    
    
    #   Pulling forecast data from Weather Underground,... or.... the FUTURE!!
    try:
        theFuture = apiPoll(lookup_curr_query)
        
        #Failing to get the forecast data should drop us out and tell us
    except Exception as e:
        print("Error: %s", e )
        sys.exit(EXIT_STATUS_ERROR)

    #   If the good day flag was thrown check today's conditions and high temp    
    if OUTPUT_GOOD_DAY:
        try:
            # Checking forecastday 0 as that signifies "today" (1, 2, 3 are the 3day forecast)
            forecast_temp = int(theFuture[fC][sFc][fCd][0][hG][fH])
            forecast_cond = theFuture[fC][sFc][fCd][0][cD]
            
            #   Ensuring both the high temp and the sunny conditions are both met then printing
            if (forecast_temp == PREF_TEMP) and (forecast_cond == PREF_COND):
                print("\n   Today will be a good day to get out of the house %s." % USER_NAME)
                print("The forecast is %s with a high of %0d F" % (forecast_cond, forecast_temp))
                
            else:
                print("\n   Today is not a good day to get out %s." % USER_NAME)
                print("The high will be %s with %s conditions" % (forecast_temp, forecast_cond))
                
        except Exception as e:
            print("Error: %s", e )
            sys.exit(EXIT_STATUS_ERROR)
            
    
            
        
    #   If the 3-day forecast flag is thrown return it
    if OUTPUT_THREE_DAY_FORECAST:
        
        try:
            three_day_dict = dict()
            print("\n   Three Day forecast for %s" % given_zip)
            
            for i in range(1, 4):
                #   Pushing each day into a seperate dict as storing them via weekday named keys causes sorting
                three_day_dict.update({'Day%s' % i : theFuture[fC][sFc][fCd][i]})
                
        except Exception as e:
            print("Error: %s", e )
            sys.exit(EXIT_STATUS_ERROR)

        if OUTPUT_JSON:
            return three_day_dict
            
        else:
            #   As a json output wasn't asked for, we are simply printing te 3day forecast to stdout
            for i in range(1, 4):
                print("\n   The forecast for %s %s %s is %s with a high of %s F" % 
                (three_day_dict['Day%s' % i]['date'][wD], 
                 three_day_dict['Day%s' % i]['date'][mN], 
                 three_day_dict['Day%s' % i]['date']['day'], 
                 three_day_dict['Day%s' % i][cD], 
                 three_day_dict['Day%s' % i][hG][fH])
                )
        
        
                
#--------------------------------  Yay running stuff!  
# Main
#-----------------------------------------------------------
def main():

    #### TODO: write a function that better handles the need for zipcodes, 
    #           specifically getting parser to require a zipcode and checking for it upon parsing 
    #
    #           Setup a schema for customizable print order - ie; run a command expect "a good day", then 3-day, etc
    #
    ##################################################################################
    
    #   Creating an internal list of args that require a zipcode.  
    #     (This should be replaced by a config file if we want to scale this out)
    valid_only_with_zipcode =[ 'currenttemp', 'threedayforecast',  'agoodday', ]

    #   Working directly with the global var for these so it affects other functions
    global OUTPUT_AVG_HIST_7_DAY_TOTAL
    global OUTPUT_AVG_HIST_7_DAY_BY_DAY
    global OUTPUT_CURRENT_TEMP
    global OUTPUT_GOOD_DAY
    global OUTPUT_THREE_DAY_FORECAST
    global API_KEY
    
    
    try:
#        # Setting up logger
#        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        
        #   Initialize arg parser
        parser = argparse.ArgumentParser(description="Process CLI args")
       
       
        #   Setting up valid CLI args
        parser.add_argument("--currenttemp",
                        help="Get the current temperature in Fahrenheit. (5-digit zipcode required)",
                        action="store_true", default=False)
                        
        #   Zip codes are the only args we take that aren't simply switch flags, process them properly.                
        parser.add_argument("--zipcode",
                        help="5-digit zip code for city you want weather info for. (last 7-days\' avg temp locked to San Jose)",
                        action="store",  default=False)
                        
        parser.add_argument("--threedayforecast",
                        help="Shows 3-day forecast for a given zipcode (5-digit zipcode required)",
                        action="store_true", default=False)
                        
        parser.add_argument("--agoodday",
                        help="Checks today's forecast to see if it will be both Sunny and exactly 68F",
                        action="store_true", default=False)
                        
        parser.add_argument("--pastweekavg",
                        help="Returns the passed 7 days\' average temperature as a total average",
                        action="store_true", default=False)
                        
        parser.add_argument("--pastweekdailyavg",
                        help="Different than \'pastweekavg\', this returns the passed 7 days\' average temps individually",
                        action="store_true", default=False)
                        
        parser.add_argument("--apikey",
                        help="Our great friends at Weather Underground require an api key to use their service, use yours, mine defaults just in case",
                        default='5f348904b60ca855/')
        
        # Parse arguments
        args = parser.parse_args()


        
        if not len(sys.argv) > 1:
            parser.error("No action specified. Please choose an action, such as: --currenttemp, --agoodday, --threedayforecast, --pastweekavg, or --pastweekdailyavg")
        
       
        
        else:
        
            #   Checking the zipcode first, if it's supplied it better be 5 numbers!
            if args.zipcode and (len(args.zipcode) !=5):
                #print(int(args.zipcode))
                print("You must enter a 5-digit zipcode, got: %s" % args.zipcode)
                sys.exit(EXIT_STATUS_ERROR)
        
            if args.zipcode and not args.zipcode.isnumeric():
                print("Error: zipcode must be 5 numbers, got %s" % args.zipcode)
                sys.exit(EXIT_STATUS_ERROR)
        
        
            #   Setting up a counter for zipcode errors
            needs_zipcode     = 0
            
            #   Setting up a counter for a single history call if either type triggers
            history_counter   = 0
            
            #   Setting up a counter for a current temperature call
            current_counter   = 0
            
            
            #   Setting up the forecast counter (increments for both a good day and 3-day calls)
            forecast_counter = 0
             
            #   Iterating over the parsed args, forcing a dict output as NameSpace is crazy.   ;-)  
            for key, value in args.__dict__.items():

                #   Checking to see if an arg's value is boolean and requires a zipcode - see TODO for this def 
                if value is bool(value) and needs_zipcode == 0:
                    #   Any arg that is setup as a switch will be acted on
                    if value == True:
                        #   If the arg requires a zipcode ensure it got one
                        if key in valid_only_with_zipcode and (args.zipcode == False):
                            
                            #   Trigger a failure if a flag requiring a zipcode didn't get one
                            needs_zipcode == needs_zipcode + 1
                            sys.exit(EXIT_STATUS_ERROR)
                                
                        else:
                            #   Placeholder for what will be done if a thrown flag doesn't need a zipcode or has the required zipcode

                            if args.currenttemp:
                                OUTPUT_CURRENT_TEMP = True
                                current_counter = current_counter + 1

                            #   Setting global var to True if it matches (We'll simply call lookAtHistory after and either or both types can return)
                            if args.pastweekavg:
                                OUTPUT_AVG_HIST_7_DAY_TOTAL = True
                                history_counter = history_counter + 1

                            #   Setting global var to True if it matches (We'll simply call lookAtHistory after and either or both types can return)                                
                            if args.pastweekdailyavg:
                                OUTPUT_AVG_HIST_7_DAY_BY_DAY = True
                                history_counter = history_counter + 1
                                         
                            #  Time for a good day
                            if args.agoodday:
                                OUTPUT_GOOD_DAY = True
                                forecast_counter = forecast_counter + 1
                                
                            #   Setting global var to true if we want a 3-day forecast    
                            if args.threedayforecast:    
                                OUTPUT_THREE_DAY_FORECAST = True
                                forecast_counter = forecast_counter +1
                                        
                    else:
                        pass
            
            #   apikey never needs a zipcode. If we threw apikey we'll store it in the global var
            if args.apikey:
                try:
                    API_KEY = '%s' % (args.apikey + '/')
                except Exception as e:
                    print("Error: Weather Underground API key  %s",  e)
                    sys.exit(EXIT_STATUS_ERROR)
            
            #   Now that we've run through the args we'll see if counters were incremented
            if history_counter >= 1:
                try:
                    lookAtHistory()
                    
                except Exception as e:
                    print("Error: %s",  e)
                    sys.exit(EXIT_STATUS_ERROR)
                    
            if current_counter >= 1:
                try:
                    currentTemp(args.zipcode)
                    
                except Exception as e:
                    print("Error: %s", e)
                    sys.exit(EXIT_STATUS_ERROR)
                    
            if forecast_counter >= 1:
                try:
                    forecastWeather(args.zipcode)

                except Exception as e:
                    print("Error: %s", e)
                    sys.exit(EXIT_STATUS_ERROR)
                    
                    
                    
                    
    
    # Catching argument errors:
    except Exception as e:
        print("Error: %s",  e)
        return EXIT_STATUS_ERROR
        
    return EXIT_STATUS_OK
    
if __name__ == '__main__':
    exit_status = main()
    sys.exit(exit_status)
    
