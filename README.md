# 🚇 BART Transit Intelligence
**End-to-End Data Engineering Pipeline & Real-Time Analytics Dashboard**

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Snowflake](https://img.shields.io/badge/Snowflake-29B5E8?style=for-the-badge&logo=snowflake&logoColor=white)](https://snowflake.com)
[![Apache Spark](https://img.shields.io/badge/Spark-E25A1C?style=for-the-badge&logo=apachespark&logoColor=white)](https://spark.apache.org/)
[![Apache Airflow](https://img.shields.io/badge/Airflow-017CEE?style=for-the-badge&logo=apacheairflow&logoColor=white)](https://airflow.apache.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)

---

## 📌 Overview
This project monitors the San Francisco Bay Area Rapid Transit (BART) system in real-time. It transforms raw API data into actionable insights, tracking system-wide delays and station performance. 

This repository showcases a transition from **Software Engineering** (scalable Java microservices) to **Data Engineering**, implementing robust ETL/ELT workflows and modern cloud data warehousing.

## 🏗️ System Architecture
The pipeline is designed for high availability and clean data separation:

* **Ingestion:** Real-time data retrieval from the BART API via Python.
* **Orchestration:** **Apache Airflow** manages complex task dependencies and schedules.
* **Processing:** **Apache Spark** performs heavy-duty data transformations and cleaning.
* **Data Warehouse:** **Snowflake** serves as the central source of truth for analytical queries.
* **Visualization:** **Streamlit** provides a live interactive dashboard featuring Plotly visualizations.

## 📁 Repository Structure
```text
├── dashboard/        # Streamlit frontend & Plotly visualization logic
├── ingestion/        # Airflow DAGs and raw API ingestion scripts
├── snowflake/        # DDLs and SQL transformation scripts
├── spark_jobs/       # PySpark processing and data cleaning jobs
├── staging/          # Local landing zone for raw data (git-ignored)
└── .gitignore        # Security layer for credentials and environment files
