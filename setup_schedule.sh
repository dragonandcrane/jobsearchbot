#!/bin/bash
# Install cron jobs for the job search bot (WSL2 primary scheduler)
# Run: bash setup_schedule.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$SCRIPT_DIR/.venv/bin/python"
CRON_LOG="$HOME/.jobsearchbot/cron.log"

mkdir -p "$HOME/.jobsearchbot"

# Build cron line
CRON_CMD="0 9,18 * * * cd $SCRIPT_DIR && $PYTHON main.py >> $CRON_LOG 2>&1"

# Check if already installed
if crontab -l 2>/dev/null | grep -qF "jobsearchbot"; then
    echo "Cron job already exists. Current crontab:"
    crontab -l | grep "jobsearchbot"
    echo ""
    read -p "Replace it? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
    # Remove old entry
    crontab -l 2>/dev/null | grep -vF "jobsearchbot" | crontab -
fi

# Add new cron entry
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "Cron job installed. Runs daily at 9:00 AM and 6:00 PM."
echo "Log file: $CRON_LOG"
echo ""
echo "Verify with: crontab -l"
echo ""
echo "NOTE: WSL2 cron requires the cron service to be running."
echo "Start it with: sudo service cron start"
echo "To auto-start cron on WSL boot, add to /etc/wsl.conf:"
echo "  [boot]"
echo "  command = service cron start"
