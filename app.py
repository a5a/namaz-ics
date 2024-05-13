# imports
import io
import zipfile
import os
import requests

import pandas as pd

from datetime import datetime, timedelta

from calendar import month_abbr

from icalendar import Calendar, Event, Alarm
import pytz

import streamlit as st



# # # # # # # # # #  Functions  # # # # # # # # # # # # # # 


def get_api_data(api_call_str: str) -> dict:
    response = requests.get(api_call_str)
    raw_output = response.json()['data']
    return raw_output


def prepare_api_call_url() -> str:

    """
    https://aladhan.com/prayer-times-api#GetCalendarByCitys
    """
    
    api_call_str = f"http://api.aladhan.com/v1/calendarByCity/" \
    f"{year}/{month}?city={city}&country={country}" \
    f"&method={method}&school={school}"

    api_call_str = api_call_str.replace(" ", "%20")

    return api_call_str


def preprocess_api_data(df):
    df_prayer_times = pd.DataFrame(pd.to_datetime(df["date"].apply(pd.Series)["gregorian"].apply(pd.Series)["date"], format= '%d-%m-%Y').dt.date, columns=["date"])

    df_temp = df["timings"].apply(pd.Series)[which_prayers].copy()
    for prayer in which_prayers:
        df_prayer_times[f"{prayer}"] = pd.to_datetime(df_temp[prayer].str[:5], format= '%H:%M')

    # round to nearest 15 minutes
    for prayer in which_prayers:
        df_prayer_times[f"{prayer}_ceil"] = df_prayer_times[prayer].apply(lambda x: x.ceil(ceil_to))

    return df_prayer_times


def calculate_ical_df(df_prayer_times, which_prayers):
    dates_for_each_time = []
    for prayer in which_prayers:
        df_temp = df_prayer_times.groupby(f"{prayer}_ceil").agg({"date":["min", "max"]}).reset_index()
        df_temp.columns = ["prayer_time", "first_date", "last_date"]
        df_temp["prayer"] = prayer

        df_temp["first_date"] = pd.to_datetime(df_temp["first_date"]) + pd.to_timedelta(df_temp["prayer_time"].dt.strftime('%H:%M:%S'))
        df_temp["last_date"] = pd.to_datetime(df_temp["last_date"]) + pd.to_timedelta(df_temp["prayer_time"].dt.strftime('%H:%M:%S'))

        df_temp["prayer_time"] = df_temp["prayer_time"].dt.time

        df_temp = df_temp[["prayer", "first_date", "last_date", "prayer_time"]].sort_values("first_date")

        dates_for_each_time.append(df_temp)

    df_dates_for_each_time = pd.concat(dates_for_each_time)

    return df_dates_for_each_time


def create_ics_text_from_definition(prayer, start_date, duration_minutes, last_date, alarm_minutes):

    # start_date = datetime(2024, 5, 1, 16, 0, 0)  # Start at 16:00
    # last_date = datetime(2024, 5, 31)

    start_date = pd.to_datetime(start_date)
    start_date = pytz.timezone('Europe/London').localize(start_date)
    duration = timedelta(minutes=duration_minutes)
    alarm_minutes = timedelta(minutes=-alarm_minutes)

    # Initialize Calendar and Event
    cal = Calendar()

    cal.add('prodid', '-//My calendar builder//asa.asa//')
    cal.add('version', '2.0')

    event = Event()

    # Add event properties
    event.add('summary', prayer)
    event.add('dtstart', start_date)
    event.add('dtend', start_date + duration)
    event.add('rrule', {
        'freq': 'weekly',
        'interval': 1,
        'byday': ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU'],  # Corrected byday parameter
        'until': last_date
    })

    # Add reminder
    alarm = Alarm()
    alarm.add('action', 'DISPLAY')
    alarm.add('description', f'Reminder: {prayer} in {alarm_minutes} minutes')
    alarm.add('trigger', alarm_minutes)
    event.add_component(alarm)

    # Add event to the calendar
    cal.add_component(event)

    # Output the calendar
    # print(cal.to_ical().decode('utf-8'))

    return cal


# # # # # # # # # #  App  # # # # # # # # # # # # # # 
st.write("""
# Prayer times ics creator
Enter settings below and click "Run" to generate the ics files.
""")

# date range
with st.expander('Select year and month'):
    this_year = datetime.now().year
    this_month = datetime.now().month
    year = st.selectbox("", range(this_year, this_year + 2 , 1))
    month_abbr = month_abbr[1:]
    report_month_str = st.radio("", month_abbr, index=this_month - 1, horizontal=True)
    month = month_abbr.index(report_month_str) + 1


# location
city = st.selectbox("City", ("London", "Oxford"))
country = st.selectbox("Country", ("United Kingdom",))

# calculation method
method_selector = st.sidebar.selectbox("Calculation method",
                      (
                        "0 - Shia Ithna-Ashari",
                        "1 - University of Islamic Sciences, Karachi",
                        "2 - Islamic Society of North America",
                        "3 - Muslim World League",
                        "4 - Umm Al-Qura University, Makkah",
                        "5 - Egyptian General Authority of Survey",
                        "7 - Institute of Geophysics, University of Tehran",
                        "8 - Gulf Region",
                        "9 - Kuwait",
                        "10 - Qatar",
                        "11 - Majlis Ugama Islam Singapura, Singapore",
                        "12 - Union Organization islamic de France",
                        "13 - Diyanet İşleri Başkanlığı, Turkey",
                        "14 - Spiritual Administration of Muslims of Russia",
                        "15 - Moonsighting Committee Worldwide (also requires shafaq parameter)",
                        "16 - Dubai (unofficial)",
                        "99 - Custom. See https://aladhan.com/calculation-methods",
                      ), index=1)

method = method_selector.split("-")[0].strip()

# school
# 0 for Shafi (or the standard way), 1 for Hanafi.
school = st.sidebar.radio(
    "School of thought",
    ["0", "1"],
    captions = ["Shafii", "Hanafi"],
    horizontal=True,
    index=1
    )




# output preferences (how many output files, rounding options)
slot_duration = st.select_slider("Length of the event (in minutes)", options=(5, 10, 15, 20, 25, 30), value=15)

ceil_to_selector = st.select_slider("Round prayer time to closest (minutes)", options=(5, 10, 15, 20, 25, 30), value=30)
ceil_to = f"{ceil_to_selector}min"

which_prayers = st.multiselect("Select prayers", ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"], 
                               default=["Dhuhr", "Asr", "Maghrib"], placeholder="Choose an option")


# # # # # # # # # #  Execution  # # # # # # # # # # # # # # 

api_call_str = prepare_api_call_url()
print(f"Going to run following api call:\n{api_call_str}")

raw_output = get_api_data(api_call_str)
df = pd.DataFrame(raw_output)

df_prayer_times = preprocess_api_data(df)
df_dates_for_each_time = calculate_ical_df(df_prayer_times, which_prayers)
# Add "ical?" column to the end of the dataframe 
df_dates_for_each_time["Generate iCal"] = True

df_selected = st.data_editor(df_dates_for_each_time, disabled=[c for c in df_dates_for_each_time.columns if c != "Generate iCal"])

df_ics = df_selected.loc[df_selected["Generate iCal"]]
# st.dataframe(df_ics)

list_of_ics = []
for prayer in which_prayers:
    prayer_times = df_ics.loc[df_ics["prayer"] == prayer]
    if prayer_times.size == 0:
        continue
    for idx, line in prayer_times.iterrows():
        list_of_ics.append((f"{prayer}_{idx}", create_ics_text_from_definition(
            line["prayer"], line["first_date"], slot_duration, line["last_date"], 10)))


buf = io.BytesIO()

with zipfile.ZipFile(buf, "x") as csv_zip:
    for filedef in list_of_ics:
            csv_zip.writestr(f"{filedef[0]}.ics", filedef[1].to_ical())

st.download_button(
    label="Download zip",
    data=buf.getvalue(),
    file_name="prayer_times.zip",
    mime="application/zip",
)
