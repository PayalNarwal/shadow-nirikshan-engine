# 🌑 Shadow Nirikshan Engine

**Shadow Nirikshan Engine** is a data-driven sustainability **decision support system** designed to detect *invisible water and electricity waste* that occurs during **periods of inactivity**.

<p align="center">
  <img src="assets/hero.png" alt="Shadow Nirikshan Engine Banner" width="800"/>
</p>

Built for **EXECUTE 5.0 Hackathon 2026**  
Theme: *Innovation for Sustainable Development*  
Team: **Binary Brains (IGDTUW)**

---

## 🚨 The Problem: Invisible Resource Waste

Most sustainability systems focus on **active usage**.  
However, on Indian campuses and large facilities, major losses occur when:

- Buildings are empty
- Pumps are left ON overnight
- Lights and equipment run without intent
- Water tanks overflow silently

These losses are:

- ❌ Not visible  
- ❌ Not reported  
- ❌ Not intentional  

We define this category as **Shadow Waste**.

---

## 💡 Core Insight: Absence Is a Signal

Instead of monitoring only usage peaks,  
**Shadow Nirikshan Engine monitors silence.**

> If no activity is expected, any significant resource usage is suspicious.

This **absence-driven intelligence** is the core innovation of our system.

---

## 🧠 Solution Overview

Shadow Nirikshan Engine is a **scheduled analysis engine** that:

1. Ingests existing operational data (no new sensors required)
2. Identifies **silence windows** using schedules
3. Learns **normal silence behavior** from historical data
4. Detects abnormal usage during inactivity
5. Generates **actionable decisions**, not just alerts
6. Adds **staff accountability, policy simulation, and human validation layers**

It is a **decision support system**, not just a monitoring dashboard.

---

## 🏗️ System Architecture (Single-Line Flow)

**Raw Data → Silence Window Detection → Baseline Learning (ML / Mean) → Shadow Waste Detection → Decision Generation → Staff Mapping → Policy Simulation → Admin Review Layer**

---

## 📊 Data Sources (Software-First)

Shadow Nirikshan works with **existing data**, even if imperfect:

- Electricity meter readings (building-level)
- Water pump ON/OFF logs
- Tank refill / tanker logs
- Class, lab, and hostel schedules
- Staff duty schedules
- Maintenance records

Designed specifically for **real Indian campuses** where data may be delayed, manual, or incomplete.

---

## ✨ Feature Highlights

- ⏱️ Scheduled cycle simulation (30-minute engine runs)
- 🤫 Silence-window based anomaly detection
- 🧠 Dual baseline engine — **ML vs Mean** comparison
- 🚨 Shadow waste anomaly detection
- 👤 Staff responsibility mapping
- 🏛️ Policy impact simulation
- 🧾 Admin anomaly review system
- 🟥 False-alarm highlighting in anomaly tables
- 🥧 Review-aware pie charts and analytics
- 💰 Cost and CO₂ impact estimation
- 🔄 Baseline-mode auto-reset simulation
- 🧩 Modular pipeline architecture
- 📊 Interactive Streamlit dashboard

---

## 🧠 Dual Baseline Engine

The system supports two baseline strategies for expected silence usage:

- **ML Baseline** — learned from historical silence windows
- **Mean Baseline** — statistical average silence usage

Users can switch baseline mode from the UI.  
The simulation resets automatically to ensure fair comparison.

---

## 👤 Staff Responsibility Mapping

Detected anomalies are automatically mapped to **on-duty staff** using staff schedules.

Outputs include:

- anomaly count per staff
- excess usage volume
- estimated cost impact
- building/resource responsibility

This enables **accountability and targeted intervention**.

---

## 🏛️ Policy Simulation Engine

Simulate sustainability policies before enforcing them.

Supported policy types:

- 💧 Pump operation restriction windows
- ⚡ Electricity shutdown windows
- 🏢 Building-specific rules

Simulation outputs:

- Water saved
- Electricity saved
- Estimated money saved
- CO₂ reduction

Helps administrators evaluate **policy impact using real anomaly data**.

---

## 🧾 Admin Review & Human-in-the-Loop Validation

A built-in governance layer allows admins to validate detected anomalies.

Admins can mark each anomaly as:

- Unreviewed
- True Waste
- False Alarm

Features:

- ✅ Review status shown directly in anomaly table
- 🟥 False alarms highlighted in red
- 🎨 Charts colored by review status
- 📊 Enables future feedback-driven tuning

This converts the system from pure detection → **validated decision intelligence**.

---

## 🔬 Innovation Angle

Unlike traditional monitoring systems that focus on **usage spikes**,  
Shadow Nirikshan Engine detects **usage during expected inactivity**.

By combining:

- silence-based anomaly detection
- human validation
- staff accountability
- policy simulation

the system acts as a **sustainability decision intelligence engine**, not just a dashboard.

---

## ⚙️ Tech Stack

- **Python 3**
- **Pandas / NumPy** — data processing
- **Scikit-learn** — ML baseline modeling
- **Streamlit** — interactive interface
- **Altair** — visual analytics
- **CSV-based ingestion** — no database dependency

---

## ▶️ How to Run the Pipeline (Terminal)

To run one complete **analysis cycle** from the terminal:

```bash
/usr/bin/python3 test_ingestion.py
```

## 🌍 Live Demo

👉 **Streamlit App:**  
https://shadow-nirikshan-engine-2026.streamlit.app/

*(The demo simulates scheduled analysis cycles and displays detected shadow waste with decisions, analytics, staff mapping, policy simulation, and admin review controls.)*
