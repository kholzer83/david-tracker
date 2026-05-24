#!/usr/bin/env python3
"""David's Trip Widget — always-on-top Tkinter desktop widget.
   Visual design: Karin's personal design system (light / warm palette).
"""

import sys
import threading
from datetime import date, datetime

try:
    import tkinter as tk
except ImportError:
    print("Tkinter is not available on this Python installation.")
    sys.exit(1)

try:
    import requests
except ImportError:
    requests = None

try:
    from zoneinfo import ZoneInfo
except ImportError:
    try:
        from backports.zoneinfo import ZoneInfo
    except ImportError:
        print("Missing timezone data: run  pip install tzdata")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Travel data
# ---------------------------------------------------------------------------

TRAVEL_DATA = [
    {"date": "2026-05-18", "city": "Durham",           "country": "USA",            "hotel": "Fairfield by Marriott Durham",             "timezone": "America/New_York"},
    {"date": "2026-05-19", "city": "Bethlehem",         "country": "USA",            "hotel": "Fairfield Inn & Suites Bethlehem PA",      "timezone": "America/New_York"},
    {"date": "2026-05-20", "city": "Plattsburgh",       "country": "USA",            "hotel": "Fairfield Inn & Suites Plattsburgh",       "timezone": "America/New_York"},
    {"date": "2026-05-21", "city": "Montreal",          "country": "Canada",         "hotel": "Residence Inn Montreal Midtown",           "timezone": "America/Toronto"},
    {"date": "2026-05-25", "city": "Cochrane",          "country": "Canada",         "hotel": "Comfort Inn & Suites Cochrane",            "timezone": "America/Toronto"},
    {"date": "2026-05-26", "city": "Thunder Bay",       "country": "Canada",         "hotel": "TownePlace Suites Thunder Bay",            "timezone": "America/Toronto"},
    {"date": "2026-05-27", "city": "Winnipeg",          "country": "Canada",         "hotel": "Fairfield by Marriott Winnipeg",           "timezone": "America/Winnipeg"},
    {"date": "2026-05-28", "city": "Calgary",           "country": "Canada",         "hotel": "Courtyard by Marriott Calgary Airport",    "timezone": "America/Edmonton"},
    {"date": "2026-05-29", "city": "Hinton",            "country": "Canada",         "hotel": "Velora Hinton Hotel",                     "timezone": "America/Edmonton"},
    {"date": "2026-05-30", "city": "Dawson Creek",      "country": "Canada",         "hotel": "Staybridge Suites Dawson Creek",           "timezone": "America/Dawson_Creek"},
    {"date": "2026-06-01", "city": "Liard Hot Springs", "country": "Canada",         "hotel": "Liard Hot Springs Lodge",                 "timezone": "America/Vancouver"},
    {"date": "2026-06-02", "city": "Whitehorse",        "country": "Canada",         "hotel": "Hyatt Place Whitehorse",                  "timezone": "America/Whitehorse"},
    {"date": "2026-06-04", "city": "Fairbanks",         "country": "USA",            "hotel": "SpringHill Suites Fairbanks",             "timezone": "America/Anchorage"},
    {"date": "2026-06-05", "city": "Anchorage",         "country": "USA",            "hotel": "Marriott Anchorage Downtown",             "timezone": "America/Anchorage"},
    {"date": "2026-06-07", "city": "Flying home",       "country": "ANC->SEA->LHR",  "hotel": "Alaska Airlines + British Airways",       "timezone": "America/Anchorage"},
    {"date": "2026-06-08", "city": "Venice",            "country": "Italy",          "hotel": "Arrived home via VCE",                    "timezone": "Europe/Rome"},
]

VIENNA_TZ  = ZoneInfo("Europe/Vienna")
TRIP_START = date.fromisoformat(TRAVEL_DATA[0]["date"])
TRIP_END   = date.fromisoformat(TRAVEL_DATA[-1]["date"])


# ---------------------------------------------------------------------------
# Design system — Karin's light palette
# ---------------------------------------------------------------------------

BG       = "#F8F6F2"   # warm off-white background
BG_CARD  = "#FFFFFF"   # card / section surface
BG_TINT  = "#FBF9F7"   # inner tint rows
BG_HDR   = "#E07A5F"   # terracotta header bar
SEP      = "#E8E4DF"   # separator lines & outer border
ACCENT   = "#3D7AB5"   # steel blue — section labels & info
SAGE     = "#81B29A"   # sage green — success, visited, progress fill
TERRA    = "#E07A5F"   # terracotta — active/current, depart today
AMBER    = "#C68B4A"   # warm amber — depart tomorrow
TEXT     = "#2D2D2D"   # primary text charcoal
DIM      = "#6B6560"   # secondary / muted text
MUTED    = "#A8A29C"   # caption / label text
HDR_TEXT = "#FFFFFF"   # white text on terracotta header
BAR_BG   = "#E8E4DF"   # progress bar track

FONT     = "Arial"     # system font — friendly, no install needed

W        = 300         # total widget width
PAD_X    = 14          # horizontal padding inside sections
PAD_Y    = 8           # vertical padding inside sections
BAR_W    = W - PAD_X * 2 - 2
WRAP     = W - PAD_X * 2 - 20


# ---------------------------------------------------------------------------
# Data helpers  (logic unchanged)
# ---------------------------------------------------------------------------

def get_current_and_next(today: date):
    current = next_stop = None
    for entry in TRAVEL_DATA:
        if date.fromisoformat(entry["date"]) <= today:
            current = entry
        elif next_stop is None:
            next_stop = entry
    return current, next_stop


def fetch_weather(city: str):
    """Returns (line1, line2).  Runs in a background thread."""
    if requests is None:
        return "install requests library", ""
    try:
        resp = requests.get(f"https://wttr.in/{city}?format=j1", timeout=10)
        resp.raise_for_status()
        cond     = resp.json()["current_condition"][0]
        desc     = cond["weatherDesc"][0]["value"]
        temp_c   = cond["temp_C"]
        temp_f   = cond["temp_F"]
        feels_c  = cond["FeelsLikeC"]
        humidity = cond["humidity"]
        wind     = cond["windspeedKmph"]
        return (f"{desc}  |  {temp_c}C / {temp_f}F",
                f"Feels {feels_c}C   Humidity {humidity}%   Wind {wind} km/h")
    except Exception as exc:
        return f"Weather unavailable ({type(exc).__name__})", ""


def time_offset(local_dt: datetime, vienna_dt: datetime) -> str:
    h = int((local_dt.utcoffset() - vienna_dt.utcoffset()).total_seconds() / 3600)
    return f"{h:+d}h" if h != 0 else "same tz"


# ---------------------------------------------------------------------------
# Widget class
# ---------------------------------------------------------------------------

class TripWidget:

    def __init__(self, root: tk.Tk):
        self.root           = root
        self._drag_ox       = 0
        self._drag_oy       = 0
        self._minimized     = False
        self._weather_city  = None
        self._weather_cache = ("", "")
        self._refresh_job   = None

        self._setup_root()
        self._build_ui()
        self._refresh_data()
        self.root.update_idletasks()
        self._place_window()
        self._tick_clock()


    # -------------------------------------------------------------------------
    # Root window
    # -------------------------------------------------------------------------

    def _setup_root(self):
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-alpha", 0.97)
        self.root.configure(bg=SEP)       # thin border bleed
        self.root.resizable(False, False)
        self.root.geometry(f"{W}x800+9999+9999")   # off-screen while building

    def _place_window(self):
        self.root.update()
        w = max(self.root.winfo_reqwidth(), W)
        h = max(self.root.winfo_reqheight(), 400)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = max(0, sw - w - 20)
        y  = 20
        h  = min(h, sh - y - 40)
        self.root.geometry(f"{w}x{h}+{x}+{y}")


    # -------------------------------------------------------------------------
    # Layout helpers
    # -------------------------------------------------------------------------

    def _sep(self):
        tk.Frame(self._container, bg=SEP, height=1).pack(fill=tk.X)

    def _section(self, label: str) -> tk.Frame:
        """Separator + steel-blue section header with small indicator bar."""
        self._sep()
        wrap = tk.Frame(self._container, bg=BG)
        wrap.pack(fill=tk.X)

        hrow = tk.Frame(wrap, bg=BG)
        hrow.pack(fill=tk.X, padx=PAD_X, pady=(7, 2))

        # 3 px coloured indicator bar
        ind = tk.Frame(hrow, bg=ACCENT, width=3, height=13)
        ind.pack_propagate(False)
        ind.pack(side=tk.LEFT, padx=(0, 7))

        tk.Label(hrow, text=label, bg=BG, fg=ACCENT,
                 font=(FONT, 8, "bold")).pack(side=tk.LEFT, anchor=tk.W)

        body = tk.Frame(wrap, bg=BG, padx=PAD_X + 4)
        body.pack(fill=tk.X, pady=(0, PAD_Y - 2))
        return body

    def _lbl(self, parent, text="", fg=None, size=10, bold=False) -> tk.Label:
        lbl = tk.Label(parent, text=text, bg=BG,
                       fg=fg or TEXT,
                       font=(FONT, size, "bold" if bold else "normal"),
                       wraplength=WRAP, justify=tk.LEFT, anchor=tk.W)
        lbl.pack(anchor=tk.W, pady=1)
        return lbl


    # -------------------------------------------------------------------------
    # UI construction
    # -------------------------------------------------------------------------

    def _build_ui(self):
        # 1 px SEP border shows around this inner frame
        self.inner = tk.Frame(self.root, bg=BG, padx=1, pady=1)
        self.inner.pack(fill=tk.BOTH, expand=True)

        self._build_header()

        self.body = tk.Frame(self.inner, bg=BG)
        self.body.pack(fill=tk.BOTH, expand=True)
        self._container = self.body

        self._build_progress()
        self._build_location()
        self._build_time()
        self._build_weather()
        self._build_next()
        self._build_footer()

    def _build_header(self):
        hdr = tk.Frame(self.inner, bg=BG_HDR, padx=PAD_X, pady=10)
        hdr.pack(fill=tk.X)

        title = tk.Label(hdr, text="David's Road Trip  2026",
                         bg=BG_HDR, fg=HDR_TEXT,
                         font=(FONT, 10, "bold"))
        title.pack(side=tk.LEFT)

        # Close  ×
        close = tk.Label(hdr, text=" × ", bg=BG_HDR, fg=HDR_TEXT,
                         font=(FONT, 12, "bold"), cursor="hand2")
        close.pack(side=tk.RIGHT, padx=(2, 0))
        close.bind("<Button-1>", lambda _: self.root.destroy())
        close.bind("<Enter>",    lambda _: close.config(fg="#FFCCCC"))
        close.bind("<Leave>",    lambda _: close.config(fg=HDR_TEXT))

        # Minimize  −
        self.min_btn = tk.Label(hdr, text=" − ", bg=BG_HDR, fg=HDR_TEXT,
                                font=(FONT, 12, "bold"), cursor="hand2")
        self.min_btn.pack(side=tk.RIGHT)
        self.min_btn.bind("<Button-1>", lambda _: self._toggle_minimize())
        self.min_btn.bind("<Enter>",    lambda _: self.min_btn.config(fg="#FFEECC"))
        self.min_btn.bind("<Leave>",    lambda _: self.min_btn.config(fg=HDR_TEXT))

        # Drag by clicking header background or title
        for w in (hdr, title):
            w.bind("<Button-1>",  self._on_drag_start)
            w.bind("<B1-Motion>", self._on_drag_move)

    def _build_progress(self):
        f = tk.Frame(self._container, bg=BG, padx=PAD_X, pady=PAD_Y)
        f.pack(fill=tk.X)

        row = tk.Frame(f, bg=BG)
        row.pack(fill=tk.X)

        self.prog_day = tk.Label(row, text="Day -- of --",
                                 bg=BG, fg=MUTED, font=(FONT, 8))
        self.prog_day.pack(side=tk.LEFT)

        self.prog_pct = tk.Label(row, text="", bg=BG, fg=SAGE,
                                 font=(FONT, 8, "bold"))
        self.prog_pct.pack(side=tk.RIGHT)

        self.bar = tk.Canvas(f, bg=BG, height=7, width=BAR_W,
                             bd=0, highlightthickness=0)
        self.bar.pack(anchor=tk.W, pady=(5, 0))
        self._redraw_bar(0.0)

    def _redraw_bar(self, frac: float):
        self.bar.delete("all")
        self.bar.create_rectangle(0, 0, BAR_W, 7, fill=BAR_BG, outline="")
        filled = max(4, int(BAR_W * min(frac, 1.0)))
        self.bar.create_rectangle(0, 0, filled, 7, fill=SAGE, outline="")

    def _build_location(self):
        f = self._section("LOCATION")
        self.loc_city  = self._lbl(f, bold=True)
        self.loc_hotel = self._lbl(f, fg=DIM, size=9)

    def _build_time(self):
        f = self._section("LOCAL TIME")

        # Local time row: [city name col] [HH:MM:SS]
        self.tf_local = tk.Frame(f, bg=BG)
        self.tf_local.pack(fill=tk.X, pady=1)
        self.time_local_city = tk.Label(self.tf_local, text="",
                                        bg=BG, fg=TERRA,
                                        font=(FONT, 9, "bold"),
                                        anchor=tk.W, width=13)
        self.time_local_city.pack(side=tk.LEFT)
        self.time_local_clock = tk.Label(self.tf_local, text="",
                                         bg=BG, fg=TEXT,
                                         font=(FONT, 10, "bold"))
        self.time_local_clock.pack(side=tk.LEFT, padx=(6, 0))

        # Vienna time row: [Vienna col] [HH:MM:SS] [offset]
        self.tf_vienna = tk.Frame(f, bg=BG)
        self.tf_vienna.pack(fill=tk.X, pady=1)
        tk.Label(self.tf_vienna, text="Vienna",
                 bg=BG, fg=DIM, font=(FONT, 9),
                 anchor=tk.W, width=13).pack(side=tk.LEFT)
        self.time_vienna_clock = tk.Label(self.tf_vienna, text="",
                                          bg=BG, fg=DIM,
                                          font=(FONT, 10))
        self.time_vienna_clock.pack(side=tk.LEFT, padx=(6, 0))
        self.time_offset_lbl = tk.Label(self.tf_vienna, text="",
                                        bg=BG, fg=ACCENT,
                                        font=(FONT, 8))
        self.time_offset_lbl.pack(side=tk.LEFT, padx=(8, 0))

    def _build_weather(self):
        f = self._section("WEATHER")
        self.wx1 = self._lbl(f)
        self.wx2 = self._lbl(f, fg=DIM, size=9)

    def _build_next(self):
        f = self._section("NEXT STOP")
        self.next_city    = self._lbl(f, fg=SAGE, bold=True)
        self.next_departs = self._lbl(f, size=9)
        self.next_hotel   = self._lbl(f, fg=DIM, size=9)

    def _build_footer(self):
        self._sep()
        f = tk.Frame(self._container, bg=BG, padx=PAD_X, pady=5)
        f.pack(fill=tk.X)

        self.footer = tk.Label(f, text="", bg=BG, fg=MUTED, font=(FONT, 7))
        self.footer.pack(side=tk.LEFT)

        ref = tk.Label(f, text="refresh", bg=BG, fg=MUTED,
                       font=(FONT, 7), cursor="hand2")
        ref.pack(side=tk.RIGHT)
        ref.bind("<Button-1>", lambda _: self._refresh_data(force_weather=True))
        ref.bind("<Enter>",    lambda _: ref.config(fg=ACCENT))
        ref.bind("<Leave>",    lambda _: ref.config(fg=MUTED))


    # -------------------------------------------------------------------------
    # Drag
    # -------------------------------------------------------------------------

    def _on_drag_start(self, event):
        self._drag_ox = event.x_root - self.root.winfo_x()
        self._drag_oy = event.y_root - self.root.winfo_y()

    def _on_drag_move(self, event):
        self.root.geometry(f"+{event.x_root - self._drag_ox}"
                           f"+{event.y_root - self._drag_oy}")

    def _toggle_minimize(self):
        x, y = self.root.winfo_x(), self.root.winfo_y()
        if self._minimized:
            self.body.pack(fill=tk.BOTH, expand=True)
            self.root.update()
            h = max(self.root.winfo_reqheight(), 400)
            self.root.geometry(f"{W}x{h}+{x}+{y}")
            self.min_btn.config(text=" − ")
            self._minimized = False
        else:
            self.body.pack_forget()
            self.root.update()
            h = self.root.winfo_reqheight()
            self.root.geometry(f"{W}x{h}+{x}+{y}")
            self.min_btn.config(text=" + ")
            self._minimized = True


    # -------------------------------------------------------------------------
    # Data refresh — runs every 60 s; weather fetched in background thread
    # -------------------------------------------------------------------------

    def _refresh_data(self, force_weather: bool = False):
        if self._refresh_job is not None:
            self.root.after_cancel(self._refresh_job)

        today = date.today()

        # -- progress bar --
        day_n     = max(1, (today - TRIP_START).days + 1)
        trip_days = (TRIP_END - TRIP_START).days
        pct       = min(100, round(100 * day_n / trip_days))
        self.prog_day.config(text=f"Day {day_n} of {trip_days}")
        self.prog_pct.config(text=f"{pct}%")
        self._redraw_bar(day_n / trip_days)

        current, next_stop = get_current_and_next(today)
        is_transit = bool(current and current["city"] == "Flying home")

        # -- location --
        if today < TRIP_START:
            days_left = (TRIP_START - today).days
            self.loc_city.config(text="Trip not started yet")
            self.loc_hotel.config(
                text=f"Departs in {days_left} day{'s' if days_left != 1 else ''}"
                     f"  ({TRIP_START.strftime('%b %d')})")
            self.wx1.config(text="--", fg=MUTED)
            self.wx2.config(text="")
        elif today > TRIP_END:
            self.loc_city.config(text="Trip complete  --  David is home!")
            self.loc_hotel.config(text="")
            self.wx1.config(text="--", fg=MUTED)
            self.wx2.config(text="")
        elif current:
            if is_transit:
                self.loc_city.config(text="In the air!  " + current["country"])
                self.loc_hotel.config(text=current["hotel"])
                self.wx1.config(text="(in transit)", fg=MUTED)
                self.wx2.config(text="")
            else:
                self.loc_city.config(
                    text=f"{current['city']}, {current['country']}")
                self.loc_hotel.config(text=current["hotel"])
                if force_weather or current["city"] != self._weather_city:
                    self._weather_city = current["city"]
                    self.wx1.config(text="Fetching weather...", fg=MUTED)
                    self.wx2.config(text="")
                    threading.Thread(
                        target=self._weather_thread,
                        args=(current["city"],),
                        daemon=True,
                    ).start()
                else:
                    l1, l2 = self._weather_cache
                    self.wx1.config(text=l1, fg=TEXT)
                    self.wx2.config(text=l2, fg=DIM)

        # -- next stop --
        if next_stop:
            nd         = date.fromisoformat(next_stop["date"])
            days_until = (nd - today).days
            if next_stop["city"] == "Flying home":
                self.next_city.config(text="Flying home!  " + next_stop["country"])
                self.next_hotel.config(text=next_stop["hotel"])
            else:
                self.next_city.config(
                    text=f"{next_stop['city']}, {next_stop['country']}")
                self.next_hotel.config(text=next_stop["hotel"])

            if days_until == 0:
                self.next_departs.config(text="Leaving TODAY", fg=TERRA)
            elif days_until == 1:
                self.next_departs.config(
                    text=f"Tomorrow  ({nd.strftime('%b %d')})", fg=AMBER)
            else:
                self.next_departs.config(
                    text=f"In {days_until} days  ({nd.strftime('%b %d')})", fg=SAGE)
        else:
            self.next_city.config(text="Final stop  --  trip complete!")
            self.next_departs.config(text="", fg=TEXT)
            self.next_hotel.config(text="")

        self.footer.config(
            text=f"Updated {datetime.now().strftime('%H:%M:%S')}")

        self._refresh_job = self.root.after(60_000, self._refresh_data)

    def _weather_thread(self, city: str):
        l1, l2 = fetch_weather(city)
        self._weather_cache = (l1, l2)
        self.root.after(0, lambda: self.wx1.config(text=l1, fg=TEXT))
        self.root.after(0, lambda: self.wx2.config(text=l2, fg=DIM))


    # -------------------------------------------------------------------------
    # 1-second clock — only touches time labels, never triggers resize
    # -------------------------------------------------------------------------

    def _tick_clock(self):
        today = date.today()
        current, _ = get_current_and_next(today)

        if current and current["city"] != "Flying home" and \
                TRIP_START <= today <= TRIP_END:
            ltz        = ZoneInfo(current["timezone"])
            local_now  = datetime.now(ltz)
            vienna_now = datetime.now(VIENNA_TZ)
            off        = time_offset(local_now, vienna_now)

            self.time_local_city.config(text=current["city"][:12])
            self.time_local_clock.config(text=local_now.strftime('%H:%M:%S'), fg=TEXT)
            self.time_vienna_clock.config(text=vienna_now.strftime('%H:%M:%S'))
            self.time_offset_lbl.config(text=f"({off})")
        else:
            vienna_now = datetime.now(VIENNA_TZ)
            self.time_local_city.config(text="")
            self.time_local_clock.config(text="")
            self.time_vienna_clock.config(text=vienna_now.strftime('%H:%M:%S'))
            self.time_offset_lbl.config(text="")

        self.root.after(1_000, self._tick_clock)


# ---------------------------------------------------------------------------

def main():
    import traceback, os
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "widget_error.log")
    try:
        root = tk.Tk()
        root.title("David's Trip")
        TripWidget(root)
        root.mainloop()
    except Exception:
        with open(log_path, "w") as f:
            traceback.print_exc(file=f)
        raise


if __name__ == "__main__":
    main()
