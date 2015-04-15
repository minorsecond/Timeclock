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
import os
import csv
import os.path
import logging
import uuid
import sqlite3

LOGFILE = "timeclock.log"
FORMATTER_STRING = r"%(levelname)s :: %(asctime)s :: in " \
                   r"%(module)s | %(message)s"

jobdb = sqlite3.connect('jobdb.db')
conn = sqlite3.connect('timesheet.db')
LOGLEVEL = logging.INFO
logging.basicConfig(filename=LOGFILE, format=FORMATTER_STRING, level=LOGLEVEL)

date = str(datetime.date.today())
day_start = datetime.datetime.now()

# Enable this flag (1) if debugging. Else leave at 0.
debug = 1


# Create data structures

# CSV columns
columns = ["Date", "Day Start", "Project Abbrev", "Project Name",
           "Project Start", "Project End", "Time Out", "Time In",
           "Day End", "ID"]

# SQL database.
with conn:
    cur = conn.cursor()
    if debug == 1:
        cur.executescript('DROP TABLE IF EXISTS timesheet')
    cur.execute('CREATE TABLE if not exists timesheet(Id INTEGER PRIMARY KEY, UUID TEXT, Lead_name TEXT, Job_name TEXT\
                , Job_abbrev TEXT, Start_time DATE, Stop_time DATE, Date DATE, Stop_type TEXT)')

# This db is used for storing total time worked for each job.
with jobdb:
    if debug == 1:
        cur.executescript('DROP TABLE IF EXISTS jobdb')
    cur.execute(
        'CREATE TABLE if not exists jobdb(Id INTEGER PRIMARY KEY, UUID TEXT, Date DATE, Lead_name TEXT, Job_name TEXT\
         , Job_abbrev TEXT, Time_worked TEXT)')

os.system('cls' if os.name == 'nt' else 'clear')


def update_now():
    """
    Updates the "now" variable, which is a datetime object with
    Year, month, day, hour, minute. e.g. 2015-2-5 13:00
    :return: datetime object with above parameters
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return now


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
    global p_uuid
    logging.debug("project_start called")
    clock_in = datetime.datetime.now().strftime('%I:%M %p')
    abbrev = raw_input("What are you working on? (ABBREV): ")
    project_name = raw_input("What is the name of this project?: ")
    lead_name = raw_input("For whom are you working?: ")
    p_uuid = str(uuid.uuid4())
    logging.debug("UUID is {}".format(p_uuid))
    logging.debug("abbrev is {}".format(abbrev))
    logging.debug("project_name is {}".format(project_name))
    print "DEBUGGING: PID = {}".format(p_uuid)
    with conn:
        cur.execute(
            "INSERT INTO timesheet(UUID, Lead_name, Job_name, Job_abbrev, Start_time, Date) VALUES(?, ?, ?, ?, ?, ?)",
            [p_uuid, lead_name, project_name, abbrev, clock_in, date])
    return p_uuid


def round_to_nearest(num, b):
    """Rounds num to the nearest base

    round_to_nearest(7, 5) -> 5
    """

    company_minutes = num + (b // 2)
    return company_minutes - (company_minutes % b)


def break_submenu():
    print "What are you doing?\n" \
          "1. Lunch\n" \
          "2. Break\n"
    answer = raw_input(">>>")
    breaktime(answer)


def sel_timesheet_row():
    """
    Returns the current job's row, using the PID generated by project_start.
    :return: the current job's row.
    """

    # Probably be better to use cur.lastrowid to select the last row, because currently it will fetch all activities
    # per PID and update them.

    with conn:
        lid = cur.lastrowid
        cur.execute(
            "SELECT UUID, Job_name, Job_abbrev, Stop_type, Stop_time, Date, Lead_name, Start_time FROM timesheet WHERE Id = ?",
            (lid,))
        sel = cur.fetchall()
        return sel


def sel_jobdb_row():
    with jobdb:
        lid = cur.lastrowid
        cur.execute(
            "SELECT Id, UUID, Date, Lead_name, Job_name, Job_abbrev, Time_worked FROM jobdb WHERE Id = ?", (lid,))
        sel_jobdb = cur.fetchall()
        return sel_jobdb

def breaktime(answer):
    """Prompts user to specify reason for break.

    :param answer: takes user input from timer function

    No real reason for this other than just general bookkeeping.
    Not a requirement. Would be nice to be able to pause the timer for breaks,
    rather than having to start the script all over again.
    """
    global job_name
    global job_abbrev
    global lead_name
    global stop_type
    global start_time
    global diff
    sel = sel_timesheet_row()

    for row in sel:
        job_name = row[1]
        job_abbrev = row[2]
        stop_type = row[3]
        lead_name = row[6]
        start_time = row[7]

    # TODO: Upon entering, check if project has been set up (see if sql entry is in memory?), otherwise
    # an error is raised because some values are undefined.

    logging.debug("Called choices with answer: {}".format(answer))
    if answer.lower() in {'1', '1.', 'lunch'}:
        now = update_now()
        sel = sel_timesheet_row()
        for row in sel:
            job_name = row[1]
            job_abbrev = row[2]
            stop_type = row[3]
            lead_name = row[6]
            start_time = row[7]
        for row in sel:
            print "Stopping {0}, ABBREV {1} for lunch at {2}".format(row[1], row[2], now)

            # TODO: Check if the current job's PID matches all entries for same abbrev on same date. This should
            # keep everything in order as far as time calculations. It should be as simple as subtracting break
            # time from total logged hours for each PID.
        stop_type = "lunch"
        with conn:
            cur.execute(
                "INSERT INTO timesheet(UUID, Job_name, Job_abbrev, Stop_type, Stop_time) VALUES(?, ?, ?, ?, ?)",
                [p_uuid, job_name, job_abbrev, stop_type, now])
        # Get time passed since beginning of task.
        # TODO: Check hours calculation!!!
        curr_time = datetime.datetime.now().strftime('%I:%M %p')
        print(start_time)
        diff = datetime.datetime.strptime(start_time, '%I:%M %p') - datetime.datetime.strptime(curr_time, '%I:%M %p')
        time = float(round_to_nearest(diff.seconds, 360)) / 3600
        with jobdb:
            cur.execute(
                "INSERT INTO jobdb(UUID, Lead_name, Job_name, Job_abbrev, Time_worked, Date) VALUES(?, ?, ?, ?, ?, ?)",
                [p_uuid, lead_name, job_name, job_abbrev, time, date]
            )
        print ("Enjoy! You worked {0} hours on {1}.").format(time, job_name)
        logging.info("Lunch break at {}".format(datetime.datetime.now()))
        raw_input("Press Enter to begin working again")
        print("Are you still working on '{}' ? (y/n)").format(job_name)
        answer = query()
        if answer:
            now = datetime.datetime.now().strftime('%I:%M %p')
            print "Resuming '{0}' at: '{1}\n' ".format(job_name, now)
            cur.execute(
                "INSERT INTO timesheet(UUID, Job_name, Job_abbrev, Stop_type, Start_time) VALUES(?, ?, ?, ?, ?)",
                [p_uuid, job_name, job_abbrev, stop_type, now])
            main_menu()
        else:
            main_menu()
        logging.info("Back from lunch at {}".format(now))
    elif answer.lower() in {'2', '2.', 'break'}:
        now = update_now()
        logging.info("Taking a break at {}".format(now))
        raw_input("Press Enter to begin working again")
        print ("Are you still working on {}? (y/n)").format(job_name)
        answer = query()
        if answer:
            # TODO: Make this actually do something
            print "Resuming '{0}' at: '{1}' ".format(job_name, now)
            logging.info("Back from break at {}".format(now))
            main_menu()
        else:
            main_menu()
    elif answer.lower() in {'3', '3.', 'heading home', 'home'}:
        print 'Take care!'
        now = update_now()
        logging.info("Clocked out at {}".format(now))
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
    Takes user input as 00:00, splits those using : as separator,
    and prints the time formatted for timesheet in tenths of an
    hour
    """
    time_input = raw_input("\nTime Formatter\n Enter hours and minutes worked today in 00:00 format: ")
    if len(time_input.split(':')) == 2:
        split_hours = time_input.split(':')[0]
        split_minutes = time_input.split(':')[1]
        round_minutes = round_to_nearest(int(split_minutes), 6)
        print "Your timesheet entry is {0}:{1}".format(split_hours, round_minutes)
        main_menu()
    else:
        print "Check input format and try again. (00:00)"
        time_formatter()


def get_time(time):
    try:
        split_hour = time.split(':')[0]
        split_minute = time.split(':')[1]
        split_minute2 = split_minute.split(' ')[0]
        split_ap = time.split(' ')[1]
        if split_ap in {'a', 'A', 'p', 'P'}:
            while split_ap in {'a', 'A'}:
                split_ap = 'AM'
            while split_ap in {'p', 'P'}:
                split_ap = 'PM'
            time_conc = split_hour + ':' + split_minute2 + ' ' + split_ap
            time = datetime.datetime.strptime(time_conc, '%I:%M %p')
            return time
        else:
            time = datetime.datetime.strptime(time, '%I:%M %p')
            return time
    except:
        print("Check time entry format and try again.")
        total_time()


def total_time():
    t_in = get_time(raw_input("Please enter your start time in 00:00 AM/PM format: "))
    t_out = get_time(raw_input("Please enter your end time in 00:00 AM/PM format: "))
    delta = t_out - t_in
    delta_minutes = float(round_to_nearest(delta.seconds, 360)) / 3600
    print "Your time sheet entry for {0} is {1} hours.".format(delta, delta_minutes)
    raw_input("\nPress enter to return to main menu.")
    main_menu()


def switch_task():
    global job_name
    global job_abbrev
    now = update_now()
    sel = sel_timesheet_row()
    stop_type = "switch task"
    for row in sel:
        job_name = row[1]
        job_abbrev = row[2]
        stop_type = row[3]
    with conn:
        cur.execute(
            "INSERT INTO timesheet(UUID, Job_name, Job_abbrev, Stop_type, Stop_time) VALUES(?, ?, ?, ?, ?)",
            [p_uuid, job_name, job_abbrev, stop_type, now])
    project_start()
    main_menu()


def report():
    print("Generating report for {0}").format(date)
    with jobdb:
        cur.execute(
            "SELECT Job_name, Job_abbrev, Time_worked, Lead_name FROM jobdb WHERE Date = ?", (date, ))
        while True:
            sel = cur.fetchone()
            # TODO: Table formatting
            print(sel)
            raw_input("Press enter to return to main menu.")
            main_menu()


def main_menu():
    """
    Main menu for program. Prompts user for function.
    Currently, options one and two are unused but
    can't be commented out.
    """
    os.system('cls' if os.name == 'nt' else 'clear')
    print "PYPER Timesheet Utility\n\n" \
          "What would you like to do?\n" \
          "1. Clock In\New Job\n" \
          "2. Switch Job\n" \
          "3. Break Time\Quit\n" \
          "4. Set up jobs/break types\n" \
          "5. Timesheet Minute Formatter\n" \
          "6. Calculate Total Time Worked\n" \
          "7. Generate Today's Timesheet\n"
    answer = raw_input(">>> ")
    if answer.lower() in {'1', '1.'}:
        project_start()
        main_menu()
    if answer.lower() in {'2', '2.'}:
        switch_task()
    if answer.lower() in {'3', '3.'}:
        break_submenu()
    # if answer.lower() in {'4', '4.'}:

    if answer.lower() in {'5', '5.'}:
        time_formatter()
    if answer.lower() in {'6', '6.'}:
        total_time()
    if answer.lower() in {'7', '7.'}:
        print(report())


if __name__ == "__main__":
    wr_timesheet = init_csv()
    main_menu()
