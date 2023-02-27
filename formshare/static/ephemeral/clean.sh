#!/bin/bash
# This assumes that FormShare is under the official docker container. Adjust if necessary
# Add an symbolic link to script in /etc/cron.daily
find /opt/formshare/formshare/static/ephemeral -name '*.js' -mmin +1440 -delete > /dev/null