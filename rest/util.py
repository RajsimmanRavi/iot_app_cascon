#import pandas as pd
import sys
import datetime
import subprocess as sp
import re
import MySQLdb

def stringify(data):
    if data:
        return data.encode('utf-8')
    else:
        return 'None'

def mac_lookup(command):
    try:
        process = sp.Popen(command, shell=True, stdout=sp.PIPE, stderr=sp.STDOUT)
        try:
            output, err = process.communicate(timeout=180) # Python3
        except:
            output, err = process.communicate() # Python2.7
    except Exception as e:
        print("Caught error while running command: %s...Exiting!" % command)
        print(str(e))
        sys.exit(1)

    if output:
        output = output.decode("utf-8")
        output = re.split(r'\t+',output)[1]
        return output.rstrip()

def parse_mac(mac):
    prefix = mac.replace(":","")[0:6]
    cmd = "grep -i "+prefix+" oui.txt"
    lookup = mac_lookup(cmd)
    return lookup

def filter_common_macs(df,comm_macs_file):

    comm_macs = list(line.strip() for line in open(comm_macs_file))
    df = df[df['mac'].isin(comm_macs)]

    return df

def read_file(f_name):

    df = pd.read_csv(f_name, parse_dates=True)

    # This removes same signal strengths of the same mac within that specific second
    df = df.drop_duplicates(keep='first')

    df['time'] = pd.to_datetime(df['time'], format='%Y/%m/%d %H:%M:%S')

    # Look at it closer
    #start_time = datetime.datetime(2016,8, 20, 9, 20)
    #end_time = datetime.datetime(2016,8, 20, 10, 45)
    #mask = (df['time'] > start_time) & (df['time'] <= end_time)
    #df = df.loc[mask]

    df = df.set_index('time')

    return df

def get_common_macs_for_tracking(df_data,min_samples=0):

    name_list = []
    for df in df_data:

        grouped_df = df.groupby('mac')

        names = []
        for name, group in grouped_df:
            group = group.resample('1T').mean().interpolate()
            group = group.strength.astype(int)
            if len(group) >= min_samples:
                names.append(name)
        name_list.append(names)

    common_macs = list(set(name_list[0]).intersection(name_list[1]))
    return common_macs

def mysql_connect(host_ip,user_name,password,database):

    conn = {}
    db = MySQLdb.connect(host=host_ip,
                         user=user_name,
                         passwd=password,
                         db=database)

    # you must create a Cursor object. It will let
    #  you execute all the queries you need
    cur = db.cursor()

    conn["cursor"] = cur
    conn["db"] = db

    return conn

def execute_mysql_query(conn,cmd):
    result = None
    while result is None:
        try:
             conn["cursor"].execute(cmd)
        except Exception as e:
             print("Error occurred while executing... %s" % e)
             pass
        else:
            print("Successfully executed query: %s on MySQL database!" % cmd)
            result = "Complete"

def insert_mysql_data(conn,data):

    try:
        conn["cursor"].execute("""INSERT INTO wifi.data (time_stamp,onion,mac,strength,company) VALUES (%s,%s,%s,%s,%s)""", (data["time_stamp"],data["onion"],data["mac"],data["strength"],data["company"]))
        conn["db"].commit()
    except Exception as e:
        print("Error occurred while executing... %s" % e)
        conn["db"].rollback
    else:
        print("Done")

def insert_mysql_stats(conn,data):

    try:
        conn["cursor"].execute("""INSERT INTO wifi.stats (time_stamp,transfer_rate,latency,length) VALUES (%s,%s,%s,%s)""", (data["time_stamp"],data["transfer_rate"],data["latency"],data["length"]))
        conn["db"].commit()
    except Exception as e:
        print("Error occurred while executing... %s" % e)
        conn["db"].rollback
    else:
        print("Done")

def fetch_mysql_data(conn,cmd):

    try:
        conn["cursor"].execute(cmd)
    except Exception as e:
        print("Error occurred while executing... %s" % e)
    else:
        print("Done")
        #r = conn["cursor"].store_result()
        rows = conn["cursor"].fetchall()
        return_dict = {}
        for x,y in rows:
            return_dict[x] = str(y)
        return return_dict

def fetch_mysql_stats(conn,cmd):
    return_dict = {}
    try:
        conn = MySQLdb.connect(host="10.2.1.12",
            user="root",
            passwd="elascale",
            db="wifi",
            cursorclass=MySQLdb.cursors.DictCursor)
        cursor = conn.cursor()
        cursor.execute(cmd)
    except Exception as e:
        print("Error occurred while executing... %s" % e)
    else:
        print("Done")
        rows = cursor.fetchall()
        for row in rows:
            return_dict[row["id"]] = str(row["time_stamp"])+","+str(row["transfer_rate"])+","+str(row["latency"])+","+str(row["length"])

        print(return_dict)
        cursor.close()
        conn.close()
        return return_dict
