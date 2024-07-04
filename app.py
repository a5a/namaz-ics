# imports
import io
import zipfile
from datetime import datetime
from calendar import month_abbr

import pandas as pd
import streamlit as st

from api import get_api_data, prepare_api_call_url, preprocess_api_data
from ics import calculate_ical_df, create_ics_text_from_definition


# # # # # # # # # #  App  # # # # # # # # # # # # # #
st.write(
    """
# Prayer times ics creator
Enter settings below and click "Run" to generate the ics files.
"""
)

# date range
with st.expander("Select year and month"):
    this_year = datetime.now().year
    this_month = datetime.now().month
    year = st.selectbox("", range(this_year, this_year + 2, 1))
    month_abbr = month_abbr[1:]
    report_month_str = st.radio("", month_abbr, index=this_month - 1, horizontal=True)
    month = month_abbr.index(report_month_str) + 1

year_and_month_string = str(year) + "_" + ("0" + str(month) if month < 10 else str(month))
st.write(year_and_month_string)

# location
city_selector = st.selectbox("City", ("London", "Oxford", "Southampton", "Other"))
if city_selector == "Other":
    city_selector_other = st.text_input("City")
    city = city_selector_other
else:
    city = city_selector

print(city)

country = st.selectbox("Country", ("United Kingdom",))

# calculation method
method_selector = st.sidebar.selectbox(
    "Calculation method",
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
    ),
    index=1,
)

method = method_selector.split("-")[0].strip()

# school
# 0 for Shafi (or the standard way), 1 for Hanafi.
school = st.sidebar.radio("School of thought", ["0", "1"], captions=["Shafii", "Hanafi"], horizontal=True, index=1)


# output preferences (how many output files, rounding options)
slot_duration = st.select_slider("Length of the event (in minutes)", options=(5, 10, 15, 20, 25, 30), value=15)

ceil_to_selector = st.select_slider("Round prayer time to closest (minutes)", options=(5, 10, 15, 20, 25, 30), value=30)
ceil_to = f"{ceil_to_selector}min"

which_prayers = st.multiselect(
    "Select prayers",
    ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"],
    default=["Dhuhr", "Asr", "Maghrib"],
    placeholder="Choose an option",
)


# # # # # # # # # #  Execution  # # # # # # # # # # # # # #

api_params = {"city": city, "country": country, "year": year, "month": month, "method": method, "school": school}

api_call_str = prepare_api_call_url(api_params)
print(f"Going to run following api call:\n{api_call_str}")

# TODO: Ensure API output is good before running the rest of the code
raw_output = get_api_data(api_call_str)
df = pd.DataFrame(raw_output)

df_prayer_times = preprocess_api_data(df, which_prayers, ceil_to)
df_dates_for_each_time = calculate_ical_df(df_prayer_times, which_prayers)

# Add "Generate iCal" column to the end of the dataframe
df_dates_for_each_time["Generate iCal"] = True

# dataframe formatted to allow clean viewing of dates and prayer times
df_view_times = df_prayer_times[[c for c in df_prayer_times.columns if "ceil" not in c]]
for c in df_view_times.columns:
    if c == "date":
        df_view_times[c] = pd.to_datetime(df_view_times[c]).dt.date
        continue
    df_view_times[c] = df_view_times[c].dt.time
with st.expander("View all timings"):
    st.dataframe(data=df_view_times, width=None, height=None, use_container_width=False, hide_index=None)

df_selected = st.data_editor(
    df_dates_for_each_time, disabled=[c for c in df_dates_for_each_time.columns if c != "Generate iCal"]
)

df_ics = df_selected.loc[df_selected["Generate iCal"]]
# st.dataframe(df_ics)

list_of_ics = []
for prayer in which_prayers:
    prayer_times = df_ics.loc[df_ics["prayer"] == prayer]
    if prayer_times.size == 0:
        continue
    for idx, line in prayer_times.iterrows():
        list_of_ics.append(
            (
                f"{prayer}_{idx}",
                create_ics_text_from_definition(
                    prayer=line["prayer"],
                    start_datetime=line["first_date"],
                    duration_minutes=slot_duration,
                    last_date=line["last_date"],
                    alarm_minutes=10,
                    df_view_times=df_view_times,
                ),
            )
        )


buf = io.BytesIO()

with zipfile.ZipFile(buf, "x") as csv_zip:
    for filedef in list_of_ics:
        csv_zip.writestr(f"{filedef[0]}_{year_and_month_string}.ics", filedef[1].to_ical())

st.download_button(
    label="Download zip",
    data=buf.getvalue(),
    file_name=f"prayer_times_{year_and_month_string}.zip",
    mime="application/zip",
)
