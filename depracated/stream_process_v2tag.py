import json
from kafka import KafkaConsumer
from cassandra.cluster import Cluster
import sys
import requests
import time, threading
from elasticsearch import Elasticsearch
from datetime import datetime

# initialize global variables for counters 
# This represents the number of msgs received within current and past period
old_counter = 0
counter = 0

# Connects to Kafka broker or Cassandra server and returns the connection result
def connect_server(server, IP):
  result = None
  while result is None:
    try:
      if server == "Kafka":
        result = KafkaConsumer('stats', bootstrap_servers=IP,request_timeout_ms=31000)
      else:
        cluster = Cluster([IP])
        result = cluster.connect()
    except KeyboardInterrupt:
      print("\nCaught Ctrl+C! Exiting Gracefully...")
      sys.exit()
    except Exception,e:
      print(str(e))
      print("Not connected yet. Reconnecting...")
      pass
  return result

def send_to_elastic_search(elastic_IP):
  global old_counter  
  num_msgs = abs(counter - old_counter)
  msg_rate = {
    'rate': num_msgs,
    'timestamp': datetime.now()
  }

  #'{ "rate" : "'+str(num_msgs)+'", "timestamp" : "'+datetime.now()+'"}'

  print("Current old_counter: "+str(old_counter))
  # update old_counter 
  old_counter = counter 
  
  print("New old_counter: "+str(old_counter))

  try:
    es = Elasticsearch([{'host': str(elastic_IP), 'port': 9200}])  
    es.index(index='sensor_stats', doc_type='rate', body=msg_rate)
  except KeyboardInterrupt:
     print("\nCaught Ctrl+C! Exiting Gracefully...") 
     sys.exit()
  except Exception, e:
    print(str(e))
    print("Could not send data rate to Elastic_search...")
  else:
    print("Successfully sent data to Elastic_search! Current msg_rate: "+str(num_msgs))
  
  # repeat call every 60 secs 
  t = threading.Timer(60, send_to_elastic_search, [elastic_IP])
  t.daemon = True
  t.start()

def main():
  KAFKA_IP = sys.argv[1]
  CASS_IP = sys.argv[2]
  ELASTIC_IP = sys.argv[3]

  consumer = connect_server("Kafka", KAFKA_IP)
  print("Connected to Kafka Broker!")
  session = connect_server("Cassandra", CASS_IP)
  print("Connected to Cassandra Database!")

  # Initialize database tables
  try:
    # Create keyspace 'stats'
    session.execute("CREATE KEYSPACE IF NOT EXISTS stats WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor':1};")
    # Create table 'data'
    session.execute("CREATE TABLE IF NOT EXISTS stats.data( data_id int PRIMARY KEY, mem_used text, mem_available text, tx_bytes bigint, rx_bytes bigint, cpu text, date text);")
  except Exception,e:
    print(str(e))
    consumer.close()
    session.shutdown()
    sys.exit()
  else: 
    print("created Keyspace 'stats' and table 'data'. Ready to ingest data...")

  # wait for 60 secs before calling the first thread
  first_thread = threading.Timer(60, send_to_elastic_search, [ELASTIC_IP])
  first_thread.daemon = True
  first_thread.start()

  for msg in consumer:
    global counter 
    counter += 1 # increase the counter

    print("counter: "+str(counter))
      
    data = json.loads(msg.value)

    rx_bytes = int(data['Network_received_bytes'])
    tx_bytes = int(data['Network_transmitted_bytes'])
    CPU = str(data['CPU'])
    mem_used = str(data['Memory_used'])
    mem_available = str(data['Memory_available'])
    timestamp = str(data['Date'])

    get_max_id = session.execute("SELECT MAX(data_id) from stats.data;")[0]
    
    for max_id in get_max_id:
      if max_id is not None:
        data_id = max_id + 1
      else:
        data_id = 1
 
    try: 
      session.execute_async("""INSERT INTO stats.data ( data_id, cpu, date, mem_available, mem_used, rx_bytes, tx_bytes) VALUES (%s, %s, %s, %s, %s, %s, %s) """, (data_id, CPU, timestamp, mem_available, mem_used, rx_bytes, tx_bytes))
    except:
      print("Could not insert data to table...")
    else:
      print("Successfully stored data in Cassandra database!")

    sys.stdout.flush()

    
  print("Shutting down Kafka and Cassandra sessions...")

  consumer.close()
  session.shutdown()
  sys.exit()

if __name__=="__main__":
  main()

