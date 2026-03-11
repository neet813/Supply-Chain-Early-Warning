# Supply Chain Early Warning System 

An automated, data-driven risk monitoring tool that detects supply chain disruptions **before they cause stockouts** — quantifying financial exposure in £ across global trade routes.

---

## What It Does

Most supply chain tools tell you what *already* went wrong. This system tells you what is *about to* go wrong.

It pulls live data from 4 real-world APIs every 24 hours, calculates a composite risk score across major shipping routes, flags critical inventory positions, and sends automated email alerts — all without manual intervention.

---

## Live Data Sources

| Source | Data | API |
|---|---|---|
| HandyBulk | Baltic Dry Index (shipping cost proxy) | Web scrape |
| World Bank | Logistics Performance Index (port efficiency) | REST API |
| NOAA | Active weather alerts (climate risk) | REST API |
| UN Comtrade | China–Germany trade volume (trade policy risk) | REST API |

---

## Risk Score Formula

```
Risk = (Conflict × 0.30) + (Shipping Cost × 0.25) + (Climate × 0.20) + (Trade Policy × 0.15) + (Port Delay × 0.10)
```

| Score | Level |
|---|---|
| ≥ 75 |  CRITICAL |
| ≥ 55 |  HIGH |
| ≥ 35 |  MEDIUM |
| < 35 |  LOW |

---

## Routes Monitored

- Asia–Europe (Red Sea)
- Asia–Europe (Suez Canal)
- Americas–Europe (Panama Canal)
- Europe–Asia (Trade Policy)

---

## Sample Output (March 2026)

```
🔴 CRITICAL — Asia-Europe Red Sea:      79.4
🟠 HIGH     — Asia-Europe Suez:         74.9
🟠 HIGH     — Europe-Asia Trade Policy: 73.4
🟠 HIGH     — Americas-Europe Panama:   59.9

TOTAL COMPANY EXPOSURE: £25,200,000
Equivalent to 29.6 days of revenue at risk
```

---

## Automated Features

- **Google Sheets integration** — appends a new row every 24 hours with timestamp, route, risk score, risk level, and financial exposure
- **Gmail alerts** — sends an automatic email when any route hits CRITICAL
- **24-hour loop** — pipeline reruns continuously without manual trigger

---

## Tech Stack

- **Python** — pandas, numpy, requests, matplotlib, seaborn
- **APIs** — World Bank, NOAA, UN Comtrade, HandyBulk
- **Google Sheets** — gspread, google-auth
- **Gmail** — smtplib (automated alerts)
- **Platform** — Google Colab

---

## Project Structure

```
Supply-Chain-Early-Warning/
│
├── Supply_Chain_Early_Warning_System.ipynb   # Main notebook
├── supply_chain_risk.png                     # Output visualisations
└── README.md
```

---

## Key Results

- Identified **£25.2M** in financial exposure across 4 trade routes
- Flagged **Electronics** as highest-risk category (4–5 days to stockout on Red Sea disruption)
- System runs fully automated — zero manual steps after setup

---

## Author

**Navneet Kaur** — Data Analyst  
[LinkedIn](https://www.linkedin.com/in/navneet-kaur-analyst/) · [GitHub](https://github.com/neet813)
