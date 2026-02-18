@echo off
REM Windows Task Scheduler backup for the job search bot
REM Run as Administrator: setup_schedule.bat

echo Creating scheduled tasks for Job Search Bot...

REM 9:00 AM daily
schtasks /create /tn "JobSearchBot_9AM" /tr "wsl -d Ubuntu -- bash -c \"cd /home/david/wslspace/jobsearchbot && .venv/bin/python main.py >> /home/david/.jobsearchbot/cron.log 2>&1\"" /sc daily /st 09:00 /f

REM 6:00 PM daily
schtasks /create /tn "JobSearchBot_6PM" /tr "wsl -d Ubuntu -- bash -c \"cd /home/david/wslspace/jobsearchbot && .venv/bin/python main.py >> /home/david/.jobsearchbot/cron.log 2>&1\"" /sc daily /st 18:00 /f

echo.
echo Tasks created. Verify with:
echo   schtasks /query /tn "JobSearchBot_9AM"
echo   schtasks /query /tn "JobSearchBot_6PM"
echo.
echo To remove:
echo   schtasks /delete /tn "JobSearchBot_9AM" /f
echo   schtasks /delete /tn "JobSearchBot_6PM" /f
