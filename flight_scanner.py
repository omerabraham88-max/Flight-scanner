import requests
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import time

SENDER_EMAIL    = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECEIVER_EMAIL  = os.environ.get("RECEIVER_EMAIL")
SERPAPI_KEY     = os.environ.get("SERPAPI_KEY")

ORIGIN         = "TLV"
DESTINATION    = "TIA"

OUTBOUND_DATES = [
    "2025-07-24", "2025-07-25", "2025-07-26", "2025-07-27",
    "2025-07-28", "2025-07-29", "2025-07-30", "2025-07-31",
    "2025-08-01", "2025-08-02", "2025-08-03",
]
RETURN_DATES = [
    "2025-08-05", "2025-08-06", "2025-08-07", "2025-08-08",
    "2025-08-09", "2025-08-10", "2025-08-11", "2025-08-12",
]

MAX_RESULTS = 10
MAX_PRICE   = 400


def fetch_flights(outbound_date, return_date=None):
    params = {
        "engine":        "google_flights",
        "departure_id":  ORIGIN,
        "arrival_id":    DESTINATION,
        "outbound_date": outbound_date,
        "currency":      "USD",
        "hl":            "en",
        "api_key":       SERPAPI_KEY,
    }
    if return_date:
        params["return_date"] = return_date
        params["type"] = "1"
    else:
        params["type"] = "2"
    try:
        resp = requests.get("https://serpapi.com/search", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("best_flights", []) + data.get("other_flights", [])
    except Exception as e:
        print(f"Error: {e}")
        return []


def parse_flight(flight, outbound_date, return_date):
    try:
        legs         = flight.get("flights", [])
        price        = flight.get("price", 0)
        duration     = flight.get("total_duration", 0)
        airline      = legs[0].get("airline", "") if legs else ""
        airline_logo = legs[0].get("airline_logo", "") if legs else ""
        dep_time     = legs[0].get("departure_airport", {}).get("time", "") if legs else ""
        arr_time     = legs[-1].get("arrival_airport", {}).get("time", "") if legs else ""
        stops        = len(legs) - 1
        booking_url  = flight.get("booking_token", "")
        return {
            "price": price, "airline": airline, "airline_logo": airline_logo,
            "outbound": outbound_date, "return": return_date or "-",
            "dep_time": dep_time, "arr_time": arr_time,
            "duration_min": duration, "stops": stops, "booking_url": booking_url,
        }
    except:
        return None


def filter_flights(flights_raw, outbound_date, return_date):
    parsed = []
    for f in flights_raw:
        p = parse_flight(f, outbound_date, return_date)
        if p and p["price"] > 0:
            if MAX_PRICE == 0 or p["price"] <= MAX_PRICE:
                parsed.append(p)
    return sorted(parsed, key=lambda x: x["price"])


def minutes_to_hm(minutes):
    h, m = minutes // 60, minutes % 60
    return f"{h}h {m}m" if m else f"{h}h"


def build_html_email(all_results):
    today = datetime.now().strftime("%d/%m/%Y")
    rows = ""
    for item in all_results[:MAX_RESULTS]:
        stops_label = "Direct" if item["stops"] == 0 else f"{item['stops']} stop"
        stops_color = "#22c55e" if item["stops"] == 0 else "#f59e0b"
        duration    = minutes_to_hm(item["duration_min"]) if item["duration_min"] else "-"
        logo_tag    = f'<img src="{item["airline_logo"]}" height="20" style="vertical-align:middle;margin-left:6px;">' if item["airline_logo"] else ""
        book_btn    = f'<a href="https://www.google.com/travel/flights?tfs={item["booking_url"]}" style="background:#1d4ed8;color:white;padding:4px 12px;border-radius:6px;text-decoration:none;font-size:13px;">Book</a>' if item["booking_url"] else ""
        rows += f"""
        <tr style="border-bottom:1px solid #e5e7eb;">
          <td style="padding:10px 8px;font-weight:600;font-size:20px;color:#1d4ed8;">${item['price']}</td>
          <td style="padding:10px 8px;">{item['airline']}{logo_tag}</td>
          <td style="padding:10px 8px;">{item['dep_time']} - {item['arr_time']}</td>
          <td style="padding:10px 8px;">{item['outbound']}</td>
          <td style="padding:10px 8px;">{item['return']}</td>
          <td style="padding:10px 8px;">{duration}</td>
          <td style="padding:10px 8px;color:{stops_color};font-weight:600;">{stops_label}</td>
          <td style="padding:10px 8px;">{book_btn}</td>
        </tr>"""

    if not rows:
        rows = '<tr><td colspan="8" style="padding:20px;text-align:center;color:#6b7280;">No flights found</td></tr>'

    return f"""<!DOCTYPE html><html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family:Arial,sans-serif;background:#f9fafb;padding:20px;">
      <div style="max-width:800px;margin:0 auto;background:white;border-radius:12px;overflow:hidden;">
        <div style="background:#1d4ed8;color:white;padding:20px 24px;">
          <h1 style="margin:0;font-size:22px;">Flights TLV to TIA</h1>
          <p style="margin:4px 0 0;opacity:0.85;font-size:14px;">Daily scan - {today}</p>
        </div>
        <div style="padding:20px 24px;overflow-x:auto;">
          <table style="width:100%;border-collapse:collapse;font-size:14px;">
            <thead><tr style="background:#f3f4f6;">
              <th style="padding:10px 8px;text-align:left;">Price</th>
              <th style="padding:10px 8px;text-align:left;">Airline</th>
              <th style="padding:10px 8px;text-align:left;">Times</th>
              <th style="padding:10px 8px;text-align:left;">Depart</th>
              <th style="padding:10px 8px;text-align:left;">Return</th>
              <th style="padding:10px 8px;text-align:left;">Duration</th>
              <th style="padding:10px 8px;text-align:left;">Stops</th>
              <th style="padding:10px 8px;text-align:left;">Book</th>
            </tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
      </div>
    </body></html>"""


def send_email(html_content, num_results):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Flights TLV-TIA | {num_results} results | {datetime.now().strftime('%d/%m/%Y')}"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
    print("Email sent!")


def main():
    print(f"Scanning flights TLV to TIA...")
    all_flights = []
    for out_date in OUTBOUND_DATES:
        for ret_date in RETURN_DATES:
            if ret_date <= out_date:
                continue
            print(f"  {out_date} -> {ret_date}")
            raw = fetch_flights(out_date, ret_date)
            all_flights.extend(filter_flights(raw, out_date, ret_date))
            time.sleep(1.2)

    all_flights.sort(key=lambda x: x["price"])
    seen, unique = set(), []
    for f in all_flights:
        key = (f["airline"], f["outbound"], f["return"], f["price"])
        if key not in seen:
            seen.add(key)
            unique.append(f)

    print(f"Found {len(unique)} flights")
    send_email(build_html_email(unique), min(len(unique), MAX_RESULTS))


if __name__ == "__main__":
    main()
  
