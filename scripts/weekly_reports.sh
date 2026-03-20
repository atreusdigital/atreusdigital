#!/bin/bash
cd /Users/nicodanduono/Desktop/AtreusDigital
LOG=/Users/nicodanduono/Desktop/AtreusDigital/logs/weekly_reports.log

echo "=== $(date) ===" >> $LOG

# Reportes en Notion
/usr/bin/python3 -m reports.meta_performance --all --days 7 >> $LOG 2>&1

# Dashboard HTML
/usr/bin/python3 -m reports.html_dashboard --days 7 >> $LOG 2>&1
