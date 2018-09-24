import re
import os
import sys
import json
import time
import base64
import socket
from datetime import datetime
import subprocess as sp
from util import *
from random import randint

import requests

def post_request(json_data):
  REST_API_IP = os.environ["REST_API_IP"]
  REST_API_PORT = os.environ["REST_API_PORT"]

  sent = False
  while (sent == False):
    try:
      r = requests.post("http://"+str(REST_API_IP)+":"+str(REST_API_PORT)+"/data", data=json_data)
    except requests.exceptions.RequestException as e:
      print("Error caused: %s. Trying again..." % str(e))
      sent = False
    else:
      print("Successfully sent! Code: %s. Reason: %s" %(str(r.status_code),str(r.reason)))
      sent = True

def send_data(stream_dict):

  json_data = json.dumps(stream_dict)
  headers = {'Content-Type': 'application/json'}
  print(json_data)

  post_request(json_data)

def main():

    directory = "/usr/src/send_data/sorted_data/"
    #directory = "/home/ubuntu/iot_app_cascon/sensor/sorted_data/"
    #os.environ["REST_API_IP"] = "10.2.1.13"
    #os.environ["REST_API_PORT"] = "6969"

    df_data = read_dir(directory)

    while 1:
        for df in df_data:
            counter = 1
            randq = randint(100,125) # random buffer size for each file
            print("random buffer size: %s" % str(randq))
            for index, row in df.iterrows():
                stream_dict = {}
                stream_dict['time_stamp'] = str(index.strftime("%Y-%m-%d %H:%M:%S"))
                stream_dict['mac'] = str(row['mac'])
                stream_dict['strength'] = str(row['strength'])
                stream_dict['onion'] = str(row['onion'])
                send_data(stream_dict)
                counter += 1

                if counter % randq == 0:
                    rand_sleep = randint(5,15)
                    print("Time to sleep for %s seconds" % str(rand_sleep))
                    time.sleep(rand_sleep)
    sys.exit()

if __name__=="__main__":
  main()

