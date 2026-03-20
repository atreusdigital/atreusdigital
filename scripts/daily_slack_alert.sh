#!/bin/bash
cd /Users/nicodanduono/Desktop/AtreusDigital
LOG=/Users/nicodanduono/Desktop/AtreusDigital/logs/daily_slack_alert.log

echo "=== $(date) ===" >> $LOG
/usr/bin/python3 -m reports.daily_slack_alert --all >> $LOG 2>&1
