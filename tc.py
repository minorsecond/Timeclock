#!/usr/bin/python
# -*- coding: ascii -*-

"""
This script is a timesheet utility designed to assist
in keeping track of projects in a project-based
job using project codes and names. It has the ability
to create CSV files, convert standard time to tenths
of an hour, and to generate reports.
"""

# PYPER (Python Project Time Tracker)
# A timeclock program for project-based jobs
# Robert Ross Wardrup, NotTheEconomist, dschetel
# 08/31/2014

import datetime
import sys
import csv
import os.path
import logging
import uuid
import sqlite3

LOGFILE = "timeclock.log"
FORMATTER_STRING = r"%(levelname)s :: %(asctime)s :: in " \
                   r"%(module)s | %(message)s"
conn = sqlite3.connect('timesheet.db')
LOGLEVEL = logging.INFO
logging.basicConfig(filename=LOGFILE, format=FORMATTER_STRING, level=LOGLEVEL)

day_start = datetime.datetime.now()
sumtime = 0
project_time = 0


# CSV columns
columns = ["Date", "Day Start", "Project Abbrev", "Project Name",
           "Project Start", "Project End", "Time Out", "Time In",
           "Day End", "ID"]

# Create SQL database.
with conn:
    cur = conn.cursor()
    cur.execute("CREATE TABLE if not exists timesheet(ID INT, Lead_name TEXT, Job_name TEXT, Job_abbrev INT, Start_time TEXT\
                , Stop_time TEXT, Date TEXT, Stop_type TEXT)")

os.system('cls' if os.name == 'nt' else 'clear')


def query():
    """Prompts user for a yes/no answer

    if user responds with 'yes', 'ye', or 'y', return True
    if user responds with 'no' or 'n', return False
    else: return None
    """

    # raw_input returns the empty string for "enter"
    yes = {'yes', 'y', 'ye', ''}
    no = {'no', 'n'}

    choice = raw_input().lower()
    if choice in yes:
        return True
    elif choice in no:
        return False
    else:
        sys.stdout.write("Please respond with 'yes' or 'no'")


def project_start():
    """
    Prompts the user for project information, creates an id for
    recalling data (will be used in the future) and returns
    project name, project abbrev and id for use in other
    functions.
    """
    # TODO: broken now that sqlite is being used.
    logging.debug("project_start called")
    abbrev = raw_input("What are you working on? (ABBREV) ")
    project_name = raw_input("What is the name of this project? ")
    pid = uuid.uuid4()
    logging.debug("UUID is {}".format(pid))
    logging.debug("abbrev is {}".format(abbrev))
    logging.debug("project_name is {}".format(project_name))
    return {'project_name': project_name,
            'abbrev': abbrev,
            'pid': pid}


def round_to_nearest(num, base=6):
    """Rounds num to the nearest base

    round_to_nearest(7, 5) -> 5
    """

    company_minutes = num + (base // 2)
    return company_minutes - (company_minutes % base)


def calc_time(t):
    """Calculate days,hours,minutes,seconds from Timer"""

    seconds = t.seconds
    days = seconds // 60 // 60 // 24
    hours = seconds // 60 // 60
    minutes = seconds // 60
    seconds %= 60
    return (days, hours, minutes, seconds)


def timer(t):
    """Timer that ends upon user interaction. Uses round_to_nearest script
    to round to nearest six-minute interval,
    to comply with work requirements.
    """

    logging.debug("timer called")

    days, hours, minutes, seconds = calc_time(t)
    print "{days} Days {hours} Hours {minutes} Minutes {seconds} Seconds".format(
        days=days, hours=hours, minutes=minutes, seconds=seconds)

    while True:
        date = t.start_time.date()  # day the timer started
        seconds = t.seconds
        logging.info("seconds set to {}".format(seconds))
        hours = seconds // 60 // 60
        minutes = seconds // 60
        seconds %= 60
        logging.debug("TIME SET! Hours: {}, Minutes: {}, Seconds: {}".format(
            hours, minutes, seconds))
        print "What are you doing?\n" \
              "1. Lunch\n" \
              "2. Break\n" \
              "3. Heading home\n" \
              "4. Switching tasks\n"
        answer = raw_input(">>>")
        response = choices(answer, t)

        # Recalculate so we have accurate end times
        days, hours, minutes, seconds = calc_time(t)
        print "{days} Days {hours} Hours {minutes} Minutes {seconds} Seconds".format(
            days=days, hours=hours, minutes=minutes, seconds=seconds)

        round_minutes = round_to_nearest(minutes)

        print"The timesheet time elapsed is: {:.0f}m".format(round_minutes)
        # Make sure same ID is used for each abbrev code used. To help
        # check consistency.

        # let's refactor this into a clocktime object that knows how to write itself
        # especially since we REALLY only need to write to this when we clock out
        # TODO: Refactor into clocktime object.
        times_out = [date, day_start, t.abbrev, t.project_name, t.start_time,
                     "timeend_placeholder", "time_out_placeholder",
                     "placeholder", "time_in_placeholder", t.pid]
        wr_timesheet.writerow(times_out)

        if response == "end of day":
            quit()

            # time.sleep(1)
            # since we're waiting for user input, we really don't need this


def begin():
    """
    Asks user for project abbrev and name, and kicks off the timer.
    This is probably going to be reused several times so I thought
    it prudent to just make it a function.
    """


def choices(answer, t):

    """Prompts user to specify reason for break.

    :param answer: takes user input from timer function
    :param t: takes time from timer.
    answer: takes input from timer function

    No real reason for this other than just general bookkeeping.
    Not a requirement. Would be nice to be able to pause the timer for breaks,
    rather than having to start the script all over again.
    """

    logging.debug("Called choices with answer: {} on Timer {!r}".format(answer, t))
    if answer.lower() in {'1', '1.', 'lunch'}:
        print 'Bon appetit'
        t.pause("lunch")
        logging.info("Lunch break at {}".format(datetime.datetime.now()))
        raw_input("Press Enter to begin working again")
        print("Are you still working on  '{}' ? (y/n)").format(t.project_name)
        answer = query()
        if answer:
            now = datetime.datetime.now()
            print "Resuming '{0}' at: '{1}' ".format(t.project_name, now)
            t.unpause()
        else:
            begin()
        logging.info("Back from lunch at {}".format(datetime.datetime.now()))
    elif answer.lower() in {'2', '2.', 'break'}:
        logging.info("Taking a break at {}".format(datetime.datetime.now()))
        t.pause("break")
        raw_input("Press Enter to begin working again")
        print "Are you still working on {}? (y/n)".format(t.abbrev)
        answer = query()
        if answer:
            now = datetime.datetime.now()
            print "Resuming '{0}' at: '{1}' " % (t.project_name, now)
            t.unpause()
            logging.info("Back from break at {}".format(now))
        else:
            begin()
    elif answer.lower() in {'3', '3.', 'heading home', 'home'}:
        print 'Take care!'
        logging.info("Clocked out at {}".format(datetime.datetime.now()))
        t.stop()
        return "end of day"


def init_csv(filename="times.csv"):
    """Initializes the csv.writer based on its filename

    init_csv('file.csv') -> csv.writer(open('file.csv', 'a'))
    creates file if it doesn't exist, and writes some default columns as a
    header
    """

    logging.debug("Called init_csv")
    if os.path.isfile(filename):
        logging.debug("{} already exists -- opening".format(filename))
        wr_timesheet = csv.writer(open(filename, "a"))
        logging.info("{} opened as a csv.writer".format(filename))
    else:
        logging.debug("{} does not exist -- creating".format(filename))
        wr_timesheet = csv.writer(open(filename, "w"))
        logging.info("{} created and opened as a csv.writer".format(
            wr_timesheet))
        wr_timesheet.writerow(columns)
        logging.debug("{} initialized with columns: {}".format(
            filename, columns))
    return wr_timesheet


def time_formatter():
    """
    Takes user input as 00:00, splits those using : as seperator,
    and prints the time formatted for timesheet in tenths of an
    hour
    """
    time_input = raw_input("\nTime Formatter\n" \
                           "Please enter hours and minutes worked today" \
                           "in 00:00 format: ")
    if len(time_input.split(':')) == 2:
        split_hours = time_input.split(':')[0]
        split_minutes = time_input.split(':')[1]
        round_minutes = round_to_nearest(int(split_minutes))
        print "Your timesheet entry is {0}:{1}".format(split_hours, round_minutes)
        time_formatter()
    else:
        print "Please check input format and try again. (00:00)"
        time_formatter()


def main_menu():
    """
    Main menu for program. Prompts user for function.
    Currently, options one and two are unused but
    can't be commented out.
    """
    print "PYPER Timesheet Utility\n\n" \
          "What would you like to do?\n" \
          "1. Clock In\n" \
          "2. Break Time\n" \
          "3. Clock Out\n" \
          "4. Set up obs/break types\n" \
          "5. Timesheet Minute Formatter\n"
    answer = raw_input(">>>")
    # if answer.lower() in {'1', '1.'}:
    # if answer.lower() in {'2', '2.'}:
    if answer.lower() in {'3', '3.'}:
        # day_start = datetime.datetime.now()
        print "\nThe day's start time is ", day_start
        begin()
    if answer.lower() in {'5', '5.'}:
        time_formatter()


if __name__ == "__main__":
    wr_timesheet = init_csv()
    main_menu()