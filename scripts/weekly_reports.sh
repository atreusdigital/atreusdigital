#!/bin/bash
cd /Users/nicodanduono/Desktop/AtreusDigital
/usr/bin/python3 -m reports.meta_performance --all --days 7 >> /Users/nicodanduono/Desktop/AtreusDigital/logs/weekly_reports.log 2>&1
