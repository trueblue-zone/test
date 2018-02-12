#!/usr/bin/env bash
myPath="/code/project/log/flask"
if [ ! -x "$myPath" ]; then
  mkdir -p "$myPath"
fi
# mkdir -p /code/project/log/flask
nohup /root/anaconda2/bin/python /code/project/manager.py | tee /code/project/log/web.log &
sleep infinity