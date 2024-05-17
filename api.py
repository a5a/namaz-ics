# # # # # # # # # #  Functions  # # # # # # # # # # # # # #


import pandas as pd
import requests


def get_api_data(api_call_str: str) -> dict:
    response = requests.get(api_call_str)
    raw_output = response.json()["data"]
    return raw_output


def prepare_api_call_url(api_params: dict) -> str:
    """
    https://aladhan.com/prayer-times-api#GetCalendarByCitys
    """
    city = api_params["city"]
    country = api_params["country"]
    year = api_params["year"]
    month = api_params["month"]
    method = api_params["method"]
    school = api_params["school"]

    api_call_str = (
        f"http://api.aladhan.com/v1/calendarByCity/"
        f"{year}/{month}?city={city}&country={country}"
        f"&method={method}&school={school}"
    )

    api_call_str = api_call_str.replace(" ", "%20")

    return api_call_str


def preprocess_api_data(df, which_prayers, ceil_to):
    df_prayer_times = pd.DataFrame(
        pd.to_datetime(df["date"].apply(pd.Series)["gregorian"].apply(pd.Series)["date"], format="%d-%m-%Y").dt.date,
        columns=["date"],
    )

    df_temp = df["timings"].apply(pd.Series)[which_prayers].copy()
    for prayer in which_prayers:
        df_prayer_times[f"{prayer}"] = pd.to_datetime(df_temp[prayer].str[:5], format="%H:%M")

    # round to nearest 15 minutes
    for prayer in which_prayers:
        df_prayer_times[f"{prayer}_ceil"] = df_prayer_times[prayer].apply(lambda x: x.ceil(ceil_to))

    return df_prayer_times
