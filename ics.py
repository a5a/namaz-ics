from icalendar import Alarm, Calendar, Event
from datetime import timedelta
import pandas as pd
import pytz


def calculate_ical_df(df_prayer_times, which_prayers):
    dates_for_each_time = []
    for prayer in which_prayers:
        df_temp = df_prayer_times.groupby(f"{prayer}_ceil").agg({"date": ["min", "max"]}).reset_index()
        df_temp.columns = ["prayer_time", "first_date", "last_date"]
        df_temp["prayer"] = prayer

        df_temp["first_date"] = pd.to_datetime(df_temp["first_date"]) + pd.to_timedelta(
            df_temp["prayer_time"].dt.strftime("%H:%M:%S")
        )
        df_temp["last_date"] = pd.to_datetime(df_temp["last_date"]) + pd.to_timedelta(
            df_temp["prayer_time"].dt.strftime("%H:%M:%S")
        )

        df_temp["prayer_time"] = df_temp["prayer_time"].dt.time

        df_temp = df_temp[["prayer", "first_date", "last_date", "prayer_time"]].sort_values("first_date")

        dates_for_each_time.append(df_temp)

    df_dates_for_each_time = pd.concat(dates_for_each_time)

    return df_dates_for_each_time


def create_ics_text_from_definition(prayer, start_date, duration_minutes, last_date, alarm_minutes):

    # start_date = datetime(2024, 5, 1, 16, 0, 0)  # Start at 16:00
    # last_date = datetime(2024, 5, 31)

    start_date = pd.to_datetime(start_date)
    start_date = pytz.timezone("Europe/London").localize(start_date)
    duration = timedelta(minutes=duration_minutes)
    alarm_minutes = timedelta(minutes=-alarm_minutes)

    # Initialize Calendar and Event
    cal = Calendar()

    cal.add("prodid", "-//My calendar builder//asa.asa//")
    cal.add("version", "2.0")

    event = Event()

    # Add event properties
    event.add("summary", prayer)
    event.add("dtstart", start_date)
    event.add("dtend", start_date + duration)
    event.add(
        "rrule",
        {
            "freq": "weekly",
            "interval": 1,
            "byday": ["MO", "TU", "WE", "TH", "FR", "SA", "SU"],  # Corrected byday parameter
            "until": last_date,
        },
    )

    # Add reminder
    alarm = Alarm()
    alarm.add("action", "DISPLAY")
    alarm.add("description", f"Reminder: {prayer} in {alarm_minutes} minutes")
    alarm.add("trigger", alarm_minutes)
    event.add_component(alarm)

    # Add event to the calendar
    cal.add_component(event)

    # Output the calendar
    # print(cal.to_ical().decode('utf-8'))

    return cal
