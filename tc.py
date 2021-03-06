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

# TODO: Find another way to encrypt.

from __future__ import print_function

import sys

if sys.version_info.major == 2:
    input = raw_input

from datetime import datetime, timedelta, date
import os
import os.path
import logging
import uuid
import csv

# Be more specific here..
from decimal import *
import shutil

try:
    from pysqlcipher import dbapi2 as sqlite
    encryption = True
except ImportError:
    encryption = False
    pass

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Job, Employee, Clocktime, Timesheet

LOGFILE = "timeclock.log"
FORMATTER_STRING = r"%(levelname)s :: %(asctime)s :: in " \
                   r"%(module)s | %(message)s"
DB_NAME = ".timesheet.db"
LOGLEVEL = logging.INFO
logging.basicConfig(filename=LOGFILE, format=FORMATTER_STRING, level=LOGLEVEL)

day_start = datetime.now()
week_num = datetime.date(day_start).isocalendar()[1]
# TODO: Move to a SQLCipher format for security.

if encryption is True:
    print("\n***PYPER TIMESHEET UTILITY***")
    DB_NAME = ".timesheet.db"
    engine = create_engine('sqlite:///.timesheet.db')

else:
    print(
        "WARNING: Unencrypted session. Install pysqlcipher3 to enable\n"
        "encryption\n")
    DB_NAME = ".timesheet.db"
    engine = create_engine('sqlite:///{}'.format(DB_NAME))

DBSession = sessionmaker(bind=engine)
session = DBSession()


def query():
    """Prompts user for a yes/no answer

    if user responds with 'yes', 'ye', or 'y', return True
    if user responds with 'no' or 'n', return False.
    else: return None

"""

    # raw_input returns the empty string for "enter"
    yes = {'yes', 'y', 'ye'}
    no = {'no', 'n', ''}

    choice = input().lower()
    if choice in yes:
        return True

    elif choice in no:
        return False

    else:
        sys.stdout.write("Please respond with 'yes' or 'no'")


def job_newline(
        abbrev,
        status,
        start_time,
        p_uuid,
        project_name,
        new,
        new_task):
    """
    Write new db row to job table, for starting new project or new week.
    :return:
    """
    current_week = get_week_days(day_start.year, week_num)
    today = datetime.today()
    bk_reason = 'pre-start_{0}'.format(project_name)
    sqlite3_backup(bk_reason)
    p_rate = 'NULL'
    if new is True:
        project_name = input("What is the name of this project?: ").upper()
        try:
            p_rate = float(input("At what rate does this job pay? (Cents): "))
        except ValueError as e:

            try:
                logging.debug(e)
                print("Check input and try again\n")
                p_rate = float(
                    input("At what rate does this job pay? (Cents): "))
            except ValueError:
                input("Press enter to return to main menu.")
                main_menu(project_name, status, start_time, p_uuid)

        logging.debug("job id is {}".format(abbrev))
        logging.debug("project_name is {}".format(project_name))

    # Set up the table row and commit.
    new_task_time = Timesheet(
        p_uuid=str(p_uuid),
        abbr=abbrev,
        name=project_name,
        date=today,
        week=current_week)
    if new is True:
        new_job = Job(
            p_uuid=str(p_uuid),
            abbr=abbrev,
            name=project_name,
            rate=p_rate)
        session.add(new_job)

    if new_task is True:
        new_task = input("Current sub-task: ")

    elif new_task is False:
        new_task = new_task

    session.add(new_task_time)
    session.commit()

    clockin(p_uuid, project_name, new_task)


def project_start(project_name, status, start_time, p_uuid):
    # TODO: Split up this function as it is too complex.

    today = datetime.today().strftime('%Y-%m-%d')
    """
    Prompts the user for project information, creates an id for
    recalling data (will be used in the future) and returns
    project name, project abbrev and id for use in other
    functions.
    """

    abbr = []
    joblist = []
    subtask = []

    if encryption is True:
        # Might have to go raw sql here.
        sel = session.query(Timesheet).order_by(Timesheet.id.desc()).all()
        job_sel = session.query(Job).order_by(Job.id.desc()).all()
        clk_sel = session.query(Clocktime).order_by(Clocktime.id.desc()).all()

    else:
        sel = session.query(Timesheet).order_by(Timesheet.id.desc()).all()
        job_sel = session.query(Job).order_by(Job.id.desc()).all()
        clk_sel = session.query(Clocktime).order_by(Clocktime.id.desc()).all()

    # Create a list of job ids, to check if new job has already been entered.
    for i in sel:
        abbr.append(i.abbr)

    for i in job_sel:
        joblist.append(i.abbr)

    for i in clk_sel:
        subtask.append(i.sub_task)

    if status == 1:
        input(
            "\nYou're already in a task."
            "Press enter to return to main menu.\n\n")
        os.system('cls' if os.name == 'nt' else 'clear')
        main_menu(project_name, status, start_time, p_uuid)

    else:
        logging.debug("project_start called")
        abbrev = input('\nWhat are you working on? (Job ID): ')

        # Check if user has previously worked under this abbrev, and prompt to
        # reuse information if so.
        if abbrev in abbr:

            if abbrev in joblist:
                job = session.query(Timesheet).filter(
                    Timesheet.abbr == abbrev).order_by(
                    Timesheet.id.desc()).first()
                print("Are you working on {0}? (y/N)".format(job.name))
                answer = query()

                if answer:
                    p_uuid = job.p_uuid
                    clktime = session.query(Clocktime).filter(
                        Clocktime.p_uuid == p_uuid).order_by(
                        Clocktime.id.desc()).first()
                    print(
                        "Are you working on sub-task {0}? (y/N)"
                        .format(clktime.sub_task))
                    answer = query()

                    if answer:
                        # Check if the job entry is for current day. If not,
                        # write to new line to enable reporting by day.
                        project_name = job.name

                        if job.date.strftime('%Y-%m-%d') == today:
                            p_uuid = job.p_uuid
                            clockin(p_uuid, project_name, clktime.sub_task)

                        else:
                            # Job is same task, on the same day. Simply restart
                            # it.
                            p_uuid = uuid.uuid4()
                            subtask = clktime.sub_task
                            job_newline(
                                abbrev,
                                status,
                                start_time,
                                p_uuid,
                                project_name,
                                False,
                                subtask)
                    else:
                        # Job is same task, on a different day. Start a new line
                        # in job table.
                        job_newline(
                            abbrev,
                            status,
                            start_time,
                            p_uuid,
                            project_name,
                            False,
                            True)

                else:

                    """
                    The abbrev in job table doesn't match reality.
                    User needs to figure out why and edit job table
                    using config function.
                    """
                    input(
                        "Problem with job id codes. Check config and"
                        "change as necessary. Press enter to return"
                        "to main menu")
                    main_menu(project_name, status, start_time, p_uuid)
            else:
                """
                Abbrev is in timesheet but not job table. Something went wrong.
                User needs to figure out why and edit tables to fix.
                """

                input(
                    "\n *** WARNING: Table discrepancy. Use config tool "
                    "to check/edit as needed. Press enter"
                    "to return to main menu. \n")
                main_menu(project_name, status, start_time, p_uuid)

        else:
            # Start new task
            p_uuid = uuid.uuid4()
            job_newline(
                abbrev,
                status,
                start_time,
                p_uuid,
                project_name,
                True,
                True)


# TODO: Implement these functions
def get_job_by_abbr(abbr):
    jobs = session.query(Job).filter_by(abbr=abbr).all()

    if len(jobs) > 1:

        # two jobs with the same abbr in here -- should this be unique? If not:
        for idx, job in enumerate(jobs, start=1):
            print("{idx}. {job.name}".format(idx=idx, job=job))
        selection = input("Which job? ")
        job = jobs[int(selection) - 1]

    elif len(jobs) == 1:
        job = jobs[0]

    else:
        return None
        # TODO: no jobs found with that info -- what do we do?
    return job


def round_to_nearest(num, b):
    """Rounds num to the nearest base

    round_to_nearest(7, 5) -> 5
    """

    company_minutes = num + (b // 2)
    return company_minutes - (company_minutes % b)


def prev_jobs(project_name, status, start_time, p_uuid):
    # TODO
    """
    Get list of previous jobs and give user option to re-open them.
    :return:
    """

    # Generate dict of previous jobs
    time_worked = session.query(Timesheet).all()
    print('Previous Jobs\n')
    print("\n{:<8} {:<15} {:<3}\n".format('Id', 'Job Name'))

    for i in time_worked:
        # jobs = {'abbr': i.abbr, 'name': i.name}
        print("{:<8} {:<15} {:<10}".format(i.abbr, i.name))
    print('Enter job ID\n')
    print('>>>')
    input("Press enter to return to main menu")
    main_menu(project_name, status, start_time, p_uuid)


def clockin(p_uuid, project_name, sub_task):
    """
    Adds time, job, date, uuid data to tables for time tracking.

    :return: None
    """
    """Backup db"""
    bk_reason = 'clockin_{0}'.format(project_name)
    sqlite3_backup(bk_reason)

    new_task_clock = Clocktime(
        p_uuid=str(p_uuid),
        time_in=datetime.now(),
        sub_task=sub_task)
    session.add(new_task_clock)
    session.commit()
    main_menu(project_name, 1, datetime.now(), p_uuid)


def clockout(project_name, status, p_uuid):
    """
    Clocks user out of project. Prints time_out (now) to clocktimes
    table for whichever row contains the samep_uuid created
    in project_start().

    :rtype : object
    :return:
    """

    context = Context(prec=3, rounding=ROUND_DOWN)
    setcontext(context)
    _sum_time = Decimal(0.0)
    sqlite3_backup('clockout')

    if status == 0:
        input(
            "You're not currently in a job. Press enter to return to main menu")
        main_menu(project_name, status, None, p_uuid)

    else:
        sel_job = session.query(Timesheet).filter(
            Timesheet.p_uuid == str(p_uuid)).first()
        job_name = sel_job.name
        job_abbrev = sel_job.abbr
        sel_clk = session.query(Clocktime).order_by(Clocktime.id.desc()).first()
        clk_id = sel_clk.id
        start_time = sel_clk.time_in

        print("Are you sure you want to clock out of {0}? (y/N)".format(job_name))
        if query():

            now = datetime.now()
            print(
                '\nStopping {0}, project ID {1} at {2}:{3} on {4}/{5}/{6}'.format(
                    job_name,
                    job_abbrev,
                    now.hour,
                    now.minute,
                    now.day,
                    now.month,
                    now.year))

            # Get difference between start time and now, and then convert to tenths
            # of an hour.
            diff = datetime.now() - start_time
            time = Decimal(diff.seconds / 3600)

            # Short tasks (6 minutes or less) still count as .1 of an hour per my
            # company's policy.
            if time < .1:
                time = Decimal(0.1)

            time_worked = Decimal(round_to_nearest(diff.seconds, 360)) / 3600
            if time_worked < .1:
                time_worked = Decimal(0.1)

            if debug == 1:
                print(
                    "Variables -- Start Time {0}. Current Time: {1}. Diff: {2}. "
                    "Time: {3}".format(start_time, datetime.now()
                                       , diff, time_worked))

                print('diff.seconds = {0}'.format(diff.seconds))
                print('time = {0}'.format(time))
                input("Press enter to continue.")
            print(
                "Enjoy! You worked {0} hours on {1}.".format(
                    round(
                        time_worked,
                        1),
                    job_name))
            input("\nPress enter to return to main menu.")
            status = 0
            """
            Update Clocktime table with time out and time worked.
            Need to match with current pid so that not all
            clock activities for the job are written to.
            """
            session.query(Clocktime). \
                filter(Clocktime.id == clk_id). \
                update({"time_out": now}, synchronize_session='fetch')

            session.query(Clocktime).filter(
                Clocktime.id == clk_id).update(
                {'tworked': Decimal(time_worked)}, synchronize_session='fetch')

            session.commit()

            # Get all rows in clocktime for current job, by p_uuid and then sum
            # these tenths of an hour.
            tworked = session.query(Clocktime).filter(
                Clocktime.p_uuid == str(p_uuid)).order_by(
                Clocktime.id.desc()).all()

            for i in tworked:

                if i.tworked is not None:
                    worked = Decimal(i.tworked)
                    _sum_time += worked

                if debug == 1:
                    print(
                        "Debugging: sum of time for {0} is {1}".format(
                            i.job_id,
                            _sum_time))
                    input('Press enter to continue')

            # Round the sum of tenths of an hour worked to the nearest tenth and
            # then update to job table.
            sum_time = Decimal(round_to_nearest(_sum_time, Decimal('0.1')))
            # Round number down to nearest tenth of an hour.

            # sum_time = Decimal(math.floor(sum_time * 10) / 10)
            session.query(Timesheet). \
                filter(Timesheet.p_uuid == str(p_uuid)). \
                update({"worked": sum_time}, synchronize_session='fetch')

            session.commit()
            main_menu(project_name, status, start_time, None)

        else:
            main_menu(project_name, status, start_time, p_uuid)


def get_week_days(year, week):
    """
    Calculates week end date for given year and week number.
    :param year:
    :param week:
    :return: Timedelta, looks like: "2004-01-04" to differentiate weeks
    """
    d = date(year, 1, 1)

    if d.weekday() > 3:
        d = d + timedelta(7 - d.weekday())

    else:
        d = d - timedelta(d.weekday())
    dlt = timedelta(days=(week - 1) * 7)

    return d + dlt + timedelta(days=5)


def time_formatter(time_input):
    """Prompts the user for hh:mm and returns a timedelta

    Takes user input as 00:00, splits those using : as seperator, and returns
    the resulting timedelta object.

    """
    FAIL_MSG = "Please check input format and try again. (00:00)"
    split = time_input.split(":")

    if len(split) != 2:
        raise ValueError(FAIL_MSG)
    try:
        hours, minutes = map(int, split)

    except ValueError:
        raise ValueError(FAIL_MSG)
    minutes = round_to_nearest(minutes, 6)
    d = datetime.timedelta(hours=hours, minutes=minutes)
    return d


def get_time(time):
    """
    Format user input time so that datetime can process it correctly.
    """
    time_conc = 0
    split_ap = 0
    split_hour = 0
    split_minute2 = 0

    # If user doesn't enter in 00:00 format, this will reformat
    # their input into 00:00 AM so that DateTime can parse it.
    if time:
        if time.split(' ')[0] in {'1', '2', '3', '4', '5', '6',
                                  '7', '8', '9', '10', '11', '12'}:
            time = time.split(' ')[0] + ':' + '00' + ' ' + time.split(' ')[1]

        try:
            split_hour = time.split(':')[0]
            split_minute = time.split(':')[1]
            split_minute2 = split_minute.split(' ')[0]
            split_ap = time.split(' ')[1]
        except IndexError:
            print("\nInvalid Input.\n")

        try:

            if split_ap in {'a', 'A', 'p', 'P'}:
                while split_ap in {'a', 'A'}:
                    split_ap = 'AM'
                while split_ap in {'p', 'P'}:
                    split_ap = 'PM'
                _time_conc = split_hour + ':' + split_minute2 + ' ' + split_ap
                time_conc = datetime.strptime(str(_time_conc), '%I:%M %p')

            else:
                time_conc = datetime.strptime(time, '%I:%M %p')

        except NameError:
            print("Check format and try again.")

    else:
        print("\nYou didn't enter anything.\n")
        raise ValueError

    return time_conc


def total_time(project_name, status, start_time, p_uuid):
    """
    Prompts user to enter start and end time,prints 1/10 of an hour to screen

    :rtype : str
    :return: None

"""
    while True:
        try:
            t_in = get_time(
                    input(
                            "Please enter your start time in 00:00 AM/PM format: "))

            t_out = get_time(
                    input(
                            "Please enter your end time in 00:00 AM/PM format: "))
        except ValueError:
            print("Try again..")
            continue
        else:
            break

        delta = t_out - t_in
        delta_minutes = float(round_to_nearest(delta.seconds, 360)) / 3600
        print("\n*** Your time sheet entry is {0} hours. ***".format(delta_minutes))
        input("\nPress enter to return to main menu.")
        main_menu(project_name, status, start_time, p_uuid)


def report(project_name, status, start_time, p_uuid):
    # TODO: Refactor to be less complex..

    """
    Menu to run reports
    :return:
    """

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("Timesheet Viewer\n"
              "1. Weekly Timesheet\n"
              "2. Daily Timesheet\n"
              "3. Main Menu\n")

        answer = input('>>> ')

        if answer.startswith('1'):
            week_report(project_name, status, start_time, p_uuid)

        elif answer.startswith('2'):
            daily_report(project_name, status, start_time, p_uuid)


def week_report(project_name, status, start_time, p_uuid):
    """
    Function to generate report for current week.
    :return: Print report for current week.
    """
    os.system('cls' if os.name == 'nt' else 'clear')
    current_week = get_week_days(day_start.year, week_num)

    # Queries job table, pulling all rows.
    time_worked = session.query(Timesheet).all()
    tasks = session.query(Clocktime).all()

    for i in tasks:
        task = {'p_uuid': i.p_uuid, 'task': i.sub_task}

    print("\n  Weekly Timesheet Report\n")
    print(
        "\n{:<18} {:<18} {:18} {:<18} {:<1}".format(
            'Id',
            'Job Name',
            'Task',
            'Hours',
            'End of Week'))
    print(
        "{:<18} {:<18} {:<18} {:<18} {:<1}".format(
            '========',
            '==========',
            '=====',
            '==========',
            '=========='))

    # Print jobs for current week.
    for i in time_worked:
        day = i.date.strftime('%Y-%m-%d')

        if datetime.date(datetime.strptime
                         (i.week, '%Y-%m-%d')) == current_week:
            worked = str(i.worked)

            if i.p_uuid == task['p_uuid']:
                _task = task['task']
            print(
                "{:<18} {:<18} {:<18} {:<18} {:<1}".format(
                    i.abbr,
                    i.name,
                    _task,
                    worked,
                    day))
    input("\nPress enter to return to main menu.")
    main_menu(project_name, status, start_time, p_uuid)


def daily_report(project_name, status, start_time, p_uuid):
    """
    Function to generate report for current day.
    :param project_name: passthru for main menu
    :param status: passthru for main menu
    :param start_time: passthru for main menu
    :param p_uuid: passthru for main menu
    :return: Print report
    """

    today = datetime.today().strftime('%Y-%m-%d')
    os.system('cls' if os.name == 'nt' else 'clear')
    # Queries job table, pulling all rows.
    time_worked = session.query(Timesheet).all()
    tasks = session.query(Clocktime).all()

    print("\n  Daily Timesheet Report\n")
    print(
        "\n{:<18} {:<18} {:18} {:<18}".format(
            'Id',
            'Job Name',
            'Task',
            'Hours'))
    print(
        "{:<18} {:<18} {:<18} {:<18}".format(
            '========',
            '==========',
            '==========',
            '=====',
            '=========='))

    # Print jobs for current day.
    for i in tasks:
        task = {'p_uuid': i.p_uuid, 'task': i.sub_task}

    for i in time_worked:

        worked = str(i.worked)
        date = i.date.strftime('%Y-%m-%d')

        if date == today:

            if i.p_uuid == task['p_uuid']:
                task = task['task']

            print(
                "{:<18} {:<18} {:<18} {:<18}".format(
                    i.abbr,
                    i.name,
                    task,
                    worked))

    input("\nPress enter to return to main menu.")

    main_menu(project_name, status, start_time, p_uuid)


def config(project_name, status, start_time, p_uuid):

    # TODO: Refactor to be less complex..

    """Configure jobs and employees"""

    global session

    # TODO: Write the db_editor script.
    def clktime_row_chooser():
        """
        Allows editing of tables, so that users can fix
        instances where they forgot to clock in/out.
        Should flag row so that it's known that it was
        manually edited.
        :return:
        """
        # Set current week, and lists
        current_week = datetime.now().isocalendar()[1]
        clk_list = []

        # Create backup of DB, entitled 'backup_data'.
        sqlite3_backup('clocktime_edit')

        # Sort Job and clocktime tables by date.
        sel_clk = session.query(Clocktime).order_by(
            Clocktime.time_in.desc()).all()

        # TODO: Create menu.
        # Print clocktime and job rows.
        print("Clocktimes for this week\n")
        for i in sel_clk:
            id = i.id
            time_in = i.time_in.strftime('%Y-%m-%d @ %I:%M %p')
            time_out = i.time_out.strftime('%Y-%m-%d @ %I:%M %p')
            day = i.time_in.strftime('%Y-%m-%d')
            week = i.time_in.isocalendar()[1]

            if week == current_week:
                print('ID: {0}, Time in: {1}, Time out: {2}'.format(id, time_in, time_out))

                clk_list.append(i.id)

        edit_id = input("\nEnter the ID for the line you would like to edit: ")

        return edit_id

    def clocktime_editor(id_to_edit):
        """
        Placeholder for code to edit clocktimes in place.
        :param: id_to_edit: number of row from clocktimes table to edit.
        :return: updated clocktime and timesheet databases.
        """

        # TODO: Write clocktime_editor function. Don't forget to also update the timeclock when user submits.


# TODO: refactor these out into module-level so they're unit-testable
    def add_job(**kwargs):
        """Helper function to create Jobs

        prompt for fields if none are provided
        """

        # Create list of current jobs for duplicate checking.
        job_sel = session.query(Job).order_by(Job.id.desc()).all()
        joblist = []

        for i in job_sel:
            joblist.append(i.abbr)

        if not kwargs:
            fields = ['name', 'abbr', 'rate']
            kwargs = {field: input("{}: ".format(field)) for
                      field in fields}

            if kwargs['name'] not in joblist:
                # store rate as int of cents/hour
                kwargs['rate'] = int(kwargs['rate']) * 100
            else:
                input('Job already exists. Press enter to return to main menu.')
                main_menu(project_name, status, start_time, p_uuid)
        new_job = Job(**kwargs)
        session.add(new_job)
        return kwargs

    def add_employee(**kwargs):
        """Helper fu
        nction to create Employees

        prompt for fields if none are provided
        """
        # TODO: Add code to check job table for existing abbr
        if not kwargs:
            fields = ['firstname', 'lastname']
            kwargs = {field: input("{}: ".format(field)) for
                      field in fields}
        new_employee = Employee(**kwargs)
        session.add(new_employee)
        return new_employee

    def edit_job(jobs):
        """Helper function to edit jobs

        Prompts for which job to edit, which field to change, and calls
        change_table_value to change it
        """
        show_tables(jobs)
        requested_job_abbr = input("Job ID? ")
        # TODO: If nothing is found, or multiple is found, handle gracefully
        job_to_edit = session.query(Job) \
            .filter_by(abbr=requested_job_abbr) \
            .one()
        print("1. Name\n"
              "2. ID\n"
              "3. Rate")
        answer = input("What do you want to change? ")

        if answer.startswith('1'):  # Change name
            val_to_change = 'name'

        elif answer.startswith('2'):  # Change abbr
            val_to_change = 'abbr'

        elif answer.startswith('3'):  # Change rate
            val_to_change = 'rate'
        old_val = getattr(job_to_edit, val_to_change)
        new_val = input("What do you want to change it to? ")

        if val_to_change == 'rate':
            new_val = int(float(new_val) * 100)
        print(job_to_edit)
        print("Changing {} to {}".format(old_val, new_val))
        confirm = input("Are you sure? (y/N): ")

        if confirm == 'y':
            change_table_value(job_to_edit, val_to_change, new_val)

        else:
            print("Cancelled")

    def edit_employee(employees):
        # TODO
        """Helper function to edit employees

        Prompts for which employee to edit, which field to change, and calls
        change_table_value to change it
        """
        pass

    def show_tables(tables):
        """Prints a table of jobs/employees"""
        for table in tables:
            print(table)

    def change_table_value(table, attr, new_val):
        """Simply changes table.attr = new_val"""
        setattr(table, attr, new_val)

    while True:
        print("What do you want to configure?\n"
              "1. Jobs\n"
              "2. Clocktimes\n"
              "3. Employees\n"
              "4. Delete Tables\n"
              "5. Back Up Tables\n"
              "6. Back\n")
        answer = input(">>> ")

        if answer.startswith('1'):
            while True:
                jobs = session.query(Job).all()
                show_tables(jobs)
                print("\n"
                      "1. Add Job\n"
                      "2. Edit Job\n"
                      "3. Back\n")
                answer = input(">>> ")

                if answer.startswith('1'):
                    new_job = add_job()
                    name = new_job['name']
                    print(
                        "\nWould you like to begin working on {0}? (y/N)".
                        format(name))
                    answer = query()

                    if answer:
                        abbrev = str(new_job['abbr'])
                        job_newline(
                            abbrev,
                            status,
                            start_time,
                            p_uuid,
                            None,
                            False)
                    else:
                        main_menu(project_name, status, start_time, p_uuid)

                elif answer.startswith('2'):
                    edit_job(jobs)

                elif answer.startswith('4'):

                    try:
                        session.commit()
                    except Exception as e:
                        logging.error("An error occurred updating "
                                      "the jobs table {}".format(e))
                        print("There was an error committing changes. "
                              "Rolling back database to last good state.")
                        session.rollback()
                    break  # break the loop and go up a level

                else:
                    print("Invalid selection")

        elif answer.startswith('2'):
            clocktime_editor()

        elif answer.startswith('3'):
            # TODO: Configure employees
            raise NotImplementedError()

        elif answer.startswith('4'):
            print('Do you wish to delete the tables? (y/N)\n')
            answer = query()

            if answer:
                print('WARNING - THIS WILL DELETE ALL DATA. PROCEED? (y/N)\n')
                answer = query()

                if answer:
                    session.query(Clocktime).delete()
                    session.query(Job).delete()
                    session.query(Timesheet).delete()
                    session.commit()

                else:
                    main_menu(project_name, status, start_time, p_uuid)

            else:
                main_menu(project_name, status, start_time, p_uuid)

        elif answer.startswith('5'):
            raise NotImplementedError

        elif answer.startswith('6'):
            break  # kick out of config function


def export_timesheet(project_name, status, start_time, p_uuid):
    """
    Export timesheet to a formatted CSV file. Use all dates.
    :return: None
    """

    outfile = open('PyperTimesheet.csv', 'wt')
    outcsv = csv.writer(outfile)
    time_worked = session.query(Timesheet).all()
    header = ('Id', 'Job Name', 'Hours Worked', 'Date', 'Week Ending')
    outcsv.writerow(header)

    for i in time_worked:
        outcsv.writerow(
            [i.abbr, i.name, i.worked, datetime.date(i.date), i.week])
    outfile.close()
    main_menu(project_name, status, start_time, p_uuid)


def imp_exp_sub(project_name, status, start_time, p_uuid):
    """
    Sub-menu for main-menu import/export option.
    This will lead to functions that read/write from CSV.
    :return:
    """

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("Import/Export Timesheet\n"
              "1. Import CSV Timesheet\n"
              "2. Export CSV Timesheet\n")

        answer = input('>>> ')

        if answer.startswith('1'):
            # TODO: CSV Parsing
            raise NotImplementedError

        elif answer.startswith('2'):
            export_timesheet(project_name, status, start_time, p_uuid)

        else:
            main_menu(project_name, status, start_time, p_uuid)


def sqlite3_backup(action):
    """Create timestamped database copy, preferably use a backup directory."""
    # path = os.path.dirname(os.path.realpath('tc.py'))

    if not os.path.isdir('.backup'):
        os.makedirs('.backup')

    backup_file = os.path.join(
        '.backup',
        os.path.basename(DB_NAME) +
        '_' +
        action +
        datetime.now().strftime("-%Y%m%d-%H%M%S"))

    # Make new backup file
    shutil.copyfile(DB_NAME, backup_file)


def clean_data():
    """Delete files older than NO_OF_DAYS days"""

    print("\n------------------------------")

    path = os.path.join(os.path.dirname(os.path.realpath('tc.py')), '.backup')

    for filename in os.listdir(path):
        file_path = os.path.join(path, filename)
        s = os.stat(file_path).st_ctime
        file_time = datetime.fromtimestamp(s)

        # Delete file if over 2 days old
        if os.path.isfile(file_path):

            if file_time < (datetime.now() - timedelta(days=2)):
                os.remove(file_path)
                print("Deleting {}...".format(file_path))


def db_recover(project_name, status, start_time, p_uuid):
    """
    Function to check last db entry and give option to recover,
    or delete. This will be useful because if the program
    crashes, the time_out fields will not be written to, causing an
    error on next run. This function should check if
    the time_out field of the last row is empty and,
    if so, give said options.

    :return: None
    """

    # if status is 0:
    sqlite3_backup('db_recover')

    # Create list of backup files
    path = os.path.join(os.path.dirname(os.path.realpath('tc.py')), '.backup')
    files = []

    for filename in os.listdir(path):
        file_path = os.path.join(path, filename)
        # s = os.stat(file_path).st_ctime
        # file_time = datetime.fromtimestamp(s)

        if os.path.isfile(file_path):
            files = sorted(
                [f for f in os.listdir(path) if f.startswith('.timesheet.db')])

    print('Most recent file = {0}. Restore this?'.format(files[-1], ))
    answer = query()
    if answer:
        shutil.move(os.path.realpath('tc.py'), os.path.join(path, 'files[-1]'))
    else:
        main_menu(project_name, status, start_time, p_uuid)


def main_menu(project_name, status, start_time, p_uuid):
    while True:
        """Main menu for program. Prompts user for function."""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("PYPER Timesheet Utility\n\n"
              "What would you like to do?\n"
              "1. Clock In\n"
              "2. Clock Out\n"
              "3. Configure\n"
              "4. Calculate Total Time Worked\n"
              "5. View Timesheets\n"
              "6. Import/Export Timesheet\n"
              "7. Quit\n")

        if status == 1:
            print(
                "*** Current job {0} started at {1}. ***\n"
                .format(project_name,
                        start_time.strftime('%I:%M %p')))

        else:
            print("*** Not currently in a job. ***\n")
        answer = input(">>> ")

        if answer.startswith('1'):
            project_start(project_name, status, start_time, p_uuid)

        if answer.startswith('2'):
            clockout(project_name, status, p_uuid)

        if answer.startswith('3'):
            config(project_name, status, start_time, p_uuid)

        if answer.startswith('4'):
            total_time(project_name, status, start_time, p_uuid)

        if answer.startswith('5'):
            report(project_name, status, start_time, p_uuid)

        if answer.startswith('6'):
            imp_exp_sub(project_name, status, start_time, p_uuid)

        if answer.startswith('7'):
            sys.exit()


if __name__ == "__main__":
    debug = 0

    # Initialize logging
    LOGFILE = "timeclock.log"
    FORMATTER_STRING = r"%(levelname)s :: %(asctime)s :: in " \
                       r"%(module)s | %(message)s"
    LOGLEVEL = logging.INFO
    logging.basicConfig(filename=LOGFILE,
                        format=FORMATTER_STRING,
                        level=LOGLEVEL)
    sqlite3_backup('startup')
    clean_data()
    os.system('cls' if os.name == 'nt' else 'clear')
    main_menu('None', 0, 0, 0)
