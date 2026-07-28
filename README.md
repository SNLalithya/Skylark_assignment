# Skylark Drones — Business Intelligence Agent

An AI-powered Business Intelligence agent that integrates dynamically with **monday.com** to answer founder and executive-level queries regarding work orders, sales pipelines, revenue metrics, and operational performance.

---

## 🌟 Key Features

- **Live monday.com Integration**: Dynamic data retrieval via GraphQL API with automatic pagination and board resolution[cite: 10].
- **Data Quality & Normalization**: Automatically normalizes mixed date formats, cleans up currency/text values, and attaches confidence scores (High/Medium/Low) based on null-value density[cite: 7, 10].
- **Multi-Board Intelligence**: Uses **LangGraph** routing to classify user queries and fetch data across Work Order and Deal boards simultaneously[cite: 7].
- **Executive Leadership Briefs**: Dedicated macro mode for generating instant operational and sales updates (type `brief` or `leadership brief`)[cite: 5, 7].
- **Interactive Conversational UI**: Built using **Chainlit** for real-time streaming, query execution status, and desktop/mobile responsiveness[cite: 5, 9].

---

## 🏗️ Architecture Overview

The system follows a modular 3-layer architecture[cite: 9]:
                 ┌────────────────────────┐
                 │   User Interface UI    │
                 │  (Chainlit Frontend)   │
                 └───────────┬────────────┘
                             │
                             ▼
                 ┌────────────────────────┐
                 │   LangGraph BI Agent   │
                 │  (Groq / Llama 3.3-70B)│
                 └───────────┬────────────┘
                             │
             ┌───────────────┴───────────────┐
             ▼                               ▼
 ┌───────────────────────┐       ┌───────────────────────┐
 │  Work Order Tracker   │       │     Deal Tracker      │
 │  (monday.com Board)   │       │  (monday.com Board)   │
 └───────────────────────┘       └───────────────────────┘

 1. **Interface Layer (`app.py`)**: Manages chat sessions, displays status spinners, and triggers agent workflows using Chainlit.
2. **Orchestration Layer (`agent.py`)**: Powered by **LangGraph** and **Groq (Llama 3.3 70B)**[cite: 7]. It routes intent (`work_orders`, `deals`, `both`, or `direct`), pulls board contexts, and constructs markdown analytical summaries[cite: 7].
3. **Data Layer (`monday_client.py`)**: Executes GraphQL calls against monday.com, normalizes date/currency schema differences, and calculates data completeness metrics[cite: 10].

---

## 📋 Prerequisites & Requirements

- Python 3.10 or higher
- Groq API Key (Free tier supported)[cite: 7, 9]
- monday.com Personal API Token[cite: 10]

---

## ⚙️ monday.com Setup Instructions

To set up the boards in monday.com manually or using the sample CSV files:

1. **Create Work Order Board**:
   - Create a new board titled **`Work Order Tracker`**.
   - Import `Work_Order_Tracker Data.xlsx - work order tracker.csv`.
   - Configure columns: Name/Item (Text), Sector (Status/Dropdown), Due Date (Date), Assigned Engineer (Text), Status (Status).

2. **Create Deals Board**:
   - Create a new board titled **`Deal Tracker`**.
   - Import `Deal funnel Data.xlsx - Deal tracker.csv`.
   - Configure columns: Name/Item (Text), Deal Value (Numbers/Currency), Stage (Status/Dropdown), Owner (Text), Close Date (Date).

3. **Retrieve Board IDs**:
   - Open each board in your browser.
   - The URL will look like `https://yourdomain.monday.com/boards/1234567890`.
   - Copy the numerical Board ID for both boards.

---

## 🚀 Local Installation & Execution

Set Up Environment Variables:
Copy .env.example to .env and fill in your API credentials:

Bash
cp .env.example .env
Edit .env:

Code snippet
MONDAY_API_KEY=your_monday_api_key_here
GROQ_API_KEY=your_groq_api_key_here
WORK_ORDER_BOARD_ID=1234567890
DEAL_BOARD_ID=0987654321
Install Dependencies:

Bash
pip install -r requirements.txt
Launch the Agent:

Bash
python -m chainlit run app.py
Access the web interface at http://localhost:8000.
