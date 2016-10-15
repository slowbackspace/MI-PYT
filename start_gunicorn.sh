#!/bin/bash
if [ -z ${PORT+x} ]; then PORT=5000; else echo "PORT is set to '$PORT'"; fi

exec gunicorn --bind 0.0.0.0:$PORT wsgi:application
