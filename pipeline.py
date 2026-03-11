import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import smtplib
import json
import re
import os
import gspread
from google.oauth2.service_account import Credentials
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ============================================================
# CONFIGURATION — values loaded from environment variables
# ============================================================

COMPANY_NAME = "NL Retail Co"
DAILY_REVENUE = 850000

CATEGORIES = {
    "Electronics":   {"daily_value": 280000, "stock_days": 18},
    "Home & Garden": {"daily_value": 180000, "stock_days": 22},
    "Textiles":      {"daily_value": 150000, "stock_days": 25},
    "Furniture":     {"daily_value": 120000, "stock_days": 30},
    "Sports":        {"daily_value":  80000, "stock_days": 20},
    "Toys":          {"daily_value":  40000, "stock_days": 28},
}

ROUTES = {
    "Asia-Europe Red Sea":      {"normal_days": 28, "disrupted_days": 42},
    "Asia-Europe Suez":         {"normal_days": 25, "disrupted_days": 38},
    "Americas-Europe Panama":   {"normal_days": 20, "disrupted_days": 30},
    "Europe-Asia Trade Policy": {"normal_days": 22, "disrupted_days": 35},
}

RISK_THRESHOLDS = {"CRITICAL": 75, "HIGH": 55, "MEDIUM": 35, "LOW": 0}

# ============================================================
# DATA PIPELINE
# ============================================================

def get_baltic_dry_index():
    try:
        url = "https://www.handybulk.com/baltic-dry-index/"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        match = re.search(r'to reach ([\d,]+) points', response.text)
        latest = int(match.group(1).replace(",", "")) if match else 2138
        if latest > 2000: risk = 80
        elif latest > 1500: risk = 60
        elif latest > 1000: risk = 40
        else: risk = 20
        print(f"✅ Baltic Dry Index: {latest} → Risk: {risk}")
        return risk
    except Exception as e:
        print(f"⚠️ BDI error: {e}")
        return 50

def get_world_bank_lpi():
    try:
        url = "http://api.worldbank.org/v2/country/CN;VN;BD;DE;NL/indicator/LP.LPI.OVRL.XQ"
        params = {"format": "json", "mrv": 1}
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        scores = {}
        for item in data[1]:
            country = item["country"]["value"]
            score = item["value"]
            if score:
                scores[country] = round(float(score), 2)
        print(f"✅ World Bank LPI: {scores}")
        return scores
    except Exception as e:
        print(f"⚠️ World Bank error: {e}")
        return {"China": 3.7, "Vietnam": 3.3, "Bangladesh": 2.6, "Germany": 4.1, "Netherlands": 4.1}

def get_weather_risk():
    try:
        url = "https://api.weather.gov/alerts/active"
        params = {"status": "actual", "message_type": "alert"}
        response = requests.get(url, params=params,
                                headers={"User-Agent": "SupplyChainMonitor"}, timeout=15)
        data = response.json()
        alert_count = len(data.get("features", []))
        risk = min(80, alert_count * 0.3)
        print(f"✅ NOAA: {alert_count} active alerts → Risk: {risk:.0f}")
        return round(risk, 1)
    except Exception as e:
        print(f"⚠️ NOAA error: {e}")
        return 30

def get_trade_policy_risk():
    try:
        url = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
        params = {"reporterCode": "156", "partnerCode": "276",
                  "cmdCode": "TOTAL", "flowCode": "X", "period": "2022"}
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        trade_value = data["data"][0].get("primaryValue", 0)
        risk_score = min(90, max(20, trade_value / 1e9 * 10))
        print(f"✅ Comtrade: ${trade_value/1e9:.1f}B → Risk: {risk_score:.0f}")
        return round(risk_score, 1)
    except Exception as e:
        print(f"⚠️ Comtrade error: {e}")
        return 45

def get_conflict_risk():
    conflict_risks = {
        "Red Sea":       90,
        "Taiwan Strait": 70,
        "Panama":        25,
        "Suez":          75,
    }
    for region, risk in conflict_risks.items():
        print(f"✅ {region}: Risk {risk} (verified March 2026)")
    return conflict_risks

# ============================================================
# RISK SCORING
# ============================================================

def calculate_route_risk(route_name, conflict_risks, bdi_risk, weather_risk, trade_risk, lpi_scores):
    region_map = {
        "Asia-Europe Red Sea": "Red Sea",
        "Asia-Europe Suez": "Suez",
        "Americas-Europe Panama": "Panama",
        "Europe-Asia Trade Policy": "Taiwan Strait"
    }
    region = region_map[route_name]
    conflict = conflict_risks.get(region, 50)
    avg_lpi = sum(lpi_scores.values()) / len(lpi_scores)
    port_delay = round((5 - avg_lpi) / 5 * 100, 1)
    risk_score = (conflict * 0.30 + bdi_risk * 0.25 + weather_risk * 0.20 +
                  trade_risk * 0.15 + port_delay * 0.10)
    risk_score = round(risk_score, 1)
    if risk_score >= 75: level = "🔴 CRITICAL"
    elif risk_score >= 55: level = "🟠 HIGH"
    elif risk_score >= 35: level = "🟡 MEDIUM"
    else: level = "🟢 LOW"
    print(f"{level} — {route_name}: {risk_score}")
    return {"route": route_name, "risk_score": risk_score, "level": level}

def calculate_stock_cover(all_scores):
    warnings = []
    for route_result in all_scores:
        route_name = route_result["route"]
        extra_delay = ROUTES[route_name]["disrupted_days"] - ROUTES[route_name]["normal_days"]
        for category, details in CATEGORIES.items():
            days_remaining = details["stock_days"] - extra_delay
            financial_risk = extra_delay * details["daily_value"]
            if days_remaining <= 0: status = "🔴 STOCKOUT"
            elif days_remaining <= 5: status = "🟠 CRITICAL"
            elif days_remaining <= 10: status = "🟡 WARNING"
            else: status = "🟢 SAFE"
            if days_remaining <= 10:
                warnings.append({
                    "route": route_name, "category": category,
                    "days_remaining": days_remaining, "financial_risk": financial_risk
                })
    return warnings

def calculate_financial_exposure(warnings):
    total = sum(w["financial_risk"] for w in warnings)
    return total

# ============================================================
# GOOGLE SHEETS
# ============================================================

def connect_to_sheets():
    # Load credentials from environment variable (JSON string)
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    creds_dict = json.loads(creds_json)
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("Early_warning_system").sheet1
    print("✅ Connected to Google Sheets!")
    return sheet

def update_sheet_no_duplicates(sheet, all_scores, warnings):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    today = datetime.now().strftime("%Y-%m-%d")

    existing_data = sheet.get_all_values()

    # Add headers if sheet is empty
    if not existing_data:
        sheet.update([["Timestamp", "Route", "Risk Score", "Risk Level", "Financial Exposure (£)"]])
        existing_data = []

    existing_combos = set()
    for row in existing_data[1:]:
        if len(row) >= 2:
            existing_combos.add((row[0][:10], row[1]))

    new_rows = []
    for score in all_scores:
        route = score["route"]
        if (today, route) not in existing_combos:
            risk_level = score["level"].replace("🔴 ", "").replace("🟠 ", "").replace("🟡 ", "").replace("🟢 ", "")
            route_exposure = sum(w["financial_risk"] for w in warnings if w["route"] == route)
            new_rows.append([timestamp, route, score["risk_score"], risk_level, route_exposure])

    if new_rows:
        sheet.append_rows(new_rows)
        print(f"✅ {len(new_rows)} new rows added to sheet.")
    else:
        print(f"⏭️ No new rows — today's data already exists.")

# ============================================================
# EMAIL ALERTS
# ============================================================

def send_alert_email(all_scores, warnings, total_exposure):
    critical_routes = [s for s in all_scores if "CRITICAL" in s["level"]]
    if not critical_routes:
        print("✅ No critical routes — no email needed.")
        return

    sender = os.environ.get("ALERT_EMAIL")
    receiver = os.environ.get("ALERT_EMAIL")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")

    body = f"""
SUPPLY CHAIN EARLY WARNING SYSTEM
{COMPANY_NAME} — Automated Risk Alert
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}

⚠️ CRITICAL ROUTES DETECTED
{'='*40}
"""
    for route in critical_routes:
        route_exposure = sum(w["financial_risk"] for w in warnings if w["route"] == route["route"])
        body += f"""
🔴 {route['route']}
   Risk Score: {route['risk_score']}/100
   Financial Exposure: £{route_exposure:,.0f}
"""

    body += f"""
{'='*40}
Total Company Exposure: £{total_exposure:,.0f}
Action Required: Review inventory levels immediately.

— Automated Supply Chain Monitor
"""

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = f"🔴 CRITICAL Supply Chain Alert — {COMPANY_NAME}"
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, app_password)
        server.sendmail(sender, receiver, msg.as_string())

    print(f"✅ Alert email sent! {len(critical_routes)} critical route(s).")

# ============================================================
# MAIN PIPELINE
# ============================================================

def run_pipeline():
    print(f"\n{'='*50}")
    print(f"🔄 Pipeline run: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    # 1. Fetch data
    bdi_risk = get_baltic_dry_index()
    lpi_scores = get_world_bank_lpi()
    weather_risk = get_weather_risk()
    trade_risk = get_trade_policy_risk()
    conflict_risks = get_conflict_risk()

    # 2. Score routes
    all_scores = []
    for route_name in ROUTES.keys():
        result = calculate_route_risk(route_name, conflict_risks, bdi_risk,
                                      weather_risk, trade_risk, lpi_scores)
        all_scores.append(result)

    # 3. Stock cover + exposure
    warnings = calculate_stock_cover(all_scores)
    total_exposure = calculate_financial_exposure(warnings)
    print(f"\n💷 Total Exposure: £{total_exposure:,.0f}")

    # 4. Update Google Sheets
    sheet = connect_to_sheets()
    update_sheet_no_duplicates(sheet, all_scores, warnings)

    # 5. Send email if needed
    send_alert_email(all_scores, warnings, total_exposure)

    print(f"\n✅ Pipeline complete.")

if __name__ == "__main__":
    run_pipeline()
