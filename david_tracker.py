#!/usr/bin/env python3
"""David's North America Road Trip Tracker - current location, local time, and live weather."""

import sys
from datetime import date, datetime

try:
    import requests
except ImportError:
    print("Missing dependency: run  pip install requests")
    sys.exit(1)

try:
    from zoneinfo import ZoneInfo
except ImportError:
    try:
        from backports.zoneinfo import ZoneInfo
    except ImportError:
        print("Missing timezone data: run  pip install tzdata")
        sys.exit(1)


TRAVEL_DATA = [
    {"date": "2026-05-18", "city": "Durham",           "country": "USA",           "hotel": "Fairfield by Marriott Durham",             "timezone": "America/New_York"},
    {"date": "2026-05-19", "city": "Bethlehem",         "country": "USA",           "hotel": "Fairfield Inn & Suites Bethlehem PA",      "timezone": "America/New_York"},
    {"date": "2026-05-20", "city": "Plattsburgh",       "country": "USA",           "hotel": "Fairfield Inn & Suites Plattsburgh",       "timezone": "America/New_York"},
    {"date": "2026-05-21", "city": "Montreal",          "country": "Canada",        "hotel": "Residence Inn Montreal Midtown",           "timezone": "America/Toronto"},
    {"date": "2026-05-25", "city": "Cochrane",          "country": "Canada",        "hotel": "Comfort Inn & Suites Cochrane",            "timezone": "America/Toronto"},
    {"date": "2026-05-26", "city": "Thunder Bay",       "country": "Canada",        "hotel": "TownePlace Suites Thunder Bay",            "timezone": "America/Toronto"},
    {"date": "2026-05-27", "city": "Winnipeg",          "country": "Canada",        "hotel": "Fairfield by Marriott Winnipeg",           "timezone": "America/Winnipeg"},
    {"date": "2026-05-28", "city": "Calgary",           "country": "Canada",        "hotel": "Courtyard by Marriott Calgary Airport",    "timezone": "America/Edmonton"},
    {"date": "2026-05-29", "city": "Hinton",            "country": "Canada",        "hotel": "Velora Hinton Hotel",                     "timezone": "America/Edmonton"},
    {"date": "2026-05-30", "city": "Dawson Creek",      "country": "Canada",        "hotel": "Staybridge Suites Dawson Creek",           "timezone": "America/Dawson_Creek"},
    {"date": "2026-06-01", "city": "Liard Hot Springs", "country": "Canada",        "hotel": "Liard Hot Springs Lodge",                 "timezone": "America/Vancouver"},
    {"date": "2026-06-02", "city": "Whitehorse",        "country": "Canada",        "hotel": "Hyatt Place Whitehorse",                  "timezone": "America/Whitehorse"},
    {"date": "2026-06-04", "city": "Fairbanks",         "country": "USA",           "hotel": "SpringHill Suites Fairbanks",             "timezone": "America/Anchorage"},
    {"date": "2026-06-05", "city": "Anchorage",         "country": "USA",           "hotel": "Marriott Anchorage Downtown",             "timezone": "America/Anchorage"},
    {"date": "2026-06-07", "city": "Flying home",       "country": "ANC->SEA->LHR", "hotel": "Alaska Airlines + British Airways",       "timezone": "America/Anchorage"},
    {"date": "2026-06-08", "city": "Venice",            "country": "Italy",         "hotel": "Arrived home via VCE",                    "timezone": "Europe/Rome"},
]

VIENNA_TZ  = ZoneInfo("Europe/Vienna")
TRIP_START = date.fromisoformat(TRAVEL_DATA[0]["date"])
TRIP_END   = date.fromisoformat(TRAVEL_DATA[-1]["date"])
WIDTH      = 64


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def rule(char="-"):
    return char * WIDTH


def header(label):
    print(f"  {label}")


def row(key, value, indent=5):
    print(f"{' ' * indent}{key:<14}{value}")


def get_current_and_next(today: date):
    """Return (current_entry, next_entry) for today."""
    current = next_stop = None
    for entry in TRAVEL_DATA:
        if date.fromisoformat(entry["date"]) <= today:
            current = entry
        elif next_stop is None:
            next_stop = entry
    return current, next_stop


def fetch_weather(city: str) -> str:
    try:
        url = f"https://wttr.in/{city}?format=j1"
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        cond     = resp.json()["current_condition"][0]
        desc     = cond["weatherDesc"][0]["value"]
        temp_c   = cond["temp_C"]
        temp_f   = cond["temp_F"]
        feels_c  = cond["FeelsLikeC"]
        humidity = cond["humidity"]
        wind     = cond["windspeedKmph"]
        return (
            f"{desc}  |  {temp_c}C / {temp_f}F"
            f"  |  Feels {feels_c}C  |  Humidity {humidity}%  |  Wind {wind} km/h"
        )
    except requests.exceptions.Timeout:
        return "(weather request timed out)"
    except Exception:
        return "(weather data unavailable)"


def time_offset_label(local_dt: datetime, vienna_dt: datetime) -> str:
    delta_s = (local_dt.utcoffset() - vienna_dt.utcoffset()).total_seconds()
    h = int(delta_s / 3600)
    return f"{h:+d}h vs Vienna" if h != 0 else "same as Vienna"


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_banner():
    print(rule("="))
    title = "DAVID'S NORTH AMERICA ROAD TRIP TRACKER  //  2026"
    print(title.center(WIDTH))
    print(rule("="))
    stops = len(TRAVEL_DATA)
    days  = (TRIP_END - TRIP_START).days
    print(f"  Durham NC  -->  Anchorage AK   |   {stops} stops   |   {days} days")
    print(rule("-"))


def main():
    today = date.today()
    print_banner()
    print()

    if today < TRIP_START:
        days_to_go = (TRIP_START - today).days
        print(f"  Trip hasn't started yet.")
        print(f"  David departs in {days_to_go} day{'s' if days_to_go != 1 else ''} "
              f"({TRIP_START.strftime('%B %d, %Y')}).")
        print()
        print(rule("="))
        return

    if today > TRIP_END:
        elapsed = (today - TRIP_END).days
        print(f"  Trip is over -- David is back home!")
        print(f"  The adventure ended {elapsed} day{'s' if elapsed != 1 else ''} ago "
              f"({TRIP_END.strftime('%B %d, %Y')}).")
        print()
        print(rule("="))
        return

    current, next_stop = get_current_and_next(today)

    if current is None:
        print("  Could not determine current location.")
        print()
        print(rule("="))
        return

    is_transit = (current["city"] == "Flying home")
    day_number = (today - TRIP_START).days + 1
    trip_days  = (TRIP_END - TRIP_START).days

    # -- current location --
    if is_transit:
        header("CURRENT STATUS   [in the air]")
        row("Route:",  current["country"])
        row("Flight:", current["hotel"])
    else:
        header("CURRENT LOCATION")
        row("City:",   f"{current['city']}, {current['country']}")
        row("Hotel:",  current["hotel"])
    print()

    # -- time comparison --
    if not is_transit:
        local_tz   = ZoneInfo(current["timezone"])
        local_now  = datetime.now(local_tz)
        vienna_now = datetime.now(VIENNA_TZ)
        offset     = time_offset_label(local_now, vienna_now)

        header("TIME")
        row(f"{current['city']}:",
            f"{local_now.strftime('%H:%M')}   ({local_now.strftime('%A, %b %d')})   [{offset}]")
        row("Vienna:",
            f"{vienna_now.strftime('%H:%M')}   ({vienna_now.strftime('%A, %b %d')})")
        print()

    # -- weather --
    if not is_transit:
        header(f"WEATHER -- {current['city']}")
        print(f"     {fetch_weather(current['city'])}")
        print()

    # -- progress bar --
    bar_width = 30
    filled = round(bar_width * (day_number / trip_days))
    bar = "[" + "#" * filled + "." * (bar_width - filled) + "]"
    header(f"TRIP PROGRESS   Day {day_number} of {trip_days}")
    print(f"     {bar}  {round(100 * day_number / trip_days)}%")
    print()

    # -- next stop --
    print(rule("-"))
    if next_stop:
        next_date  = date.fromisoformat(next_stop["date"])
        days_until = (next_date - today).days

        if next_stop["city"] == "Flying home":
            header("NEXT -->  Flying home!")
            row("Route:",  next_stop["country"])
            row("Flight:", next_stop["hotel"])
        else:
            header(f"NEXT STOP -->  {next_stop['city']}, {next_stop['country']}")
            row("Hotel:", next_stop["hotel"])

        if days_until == 0:
            row("Departs:", "TODAY -- checkout this morning!")
        elif days_until == 1:
            row("Departs:", f"Tomorrow  ({next_date.strftime('%b %d')})")
        else:
            row("Departs:", f"In {days_until} days  ({next_date.strftime('%B %d')})")
    else:
        header("This is the final stop -- trip complete!")

    print()
    print(rule("="))
    ts = datetime.now().strftime("%Y-%m-%d  %H:%M")
    print(f"  Checked: {ts}".ljust(WIDTH))
    print(rule("="))


if __name__ == "__main__":
    main()
