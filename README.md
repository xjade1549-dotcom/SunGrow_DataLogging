# Datalogging from Inverter via Pymodbus 

### by Jade Watanasoponwong 

Inverters are a crucial part of any solar cell systems, since it converts the direct current, obtained from solar cells, into an alternating current, which can be fed into households.

When running, SunGrow inverter stores real-time data inside it, such as each phase's current and voltage, all of which are able to be extracted via Modbus communication protocol.

## Objective
To log data from the inverter and store it inside a database, so that in case of an unexpected event, the latest record of inverter's data is avaliable to be inspected

## Overview
This project consists of 2 parts:

1. **Database**: a place to store logged data; used Docker's timescaleDB databse for optimized result in storing time-series data
2. **Modbus polling script**: a code to extract data from the inverter, used python's pymodbus for its simplicity

****Every files in this document needs to be in the same folder**

## Workflow

### Setting up the inverter

Before running any codes, the inverter's set up needs to be done first

1. Plug the inverter into power supply
2. Connect the inverter to a router

### Obtaining inverter's IP

After connecting the inverter to the router,

1. Select the inverter's wifi ( SGXXXXXX), and click JOIN

2. Search "11.11.11.1" in the browser, the SunGrow page will appear

3. Log in to the SunGrow page

4. Go to System > Port Parameter > Ethernet

5. Inside the Ethernet tab, there will be an IP address

![ip](ip.png)


### Running the code 

1. Enter the inverter's ip into [inverter_ip.py](inverter_ip.py)

2. Connect the computer to router's wifi

3. Execute the code in [polling_main.py](polling_main.py)


### Dockerising the polling codes (for running in remote computer)

1. Create a Dockerfile ([Dockerfile](Dockerfile))

2. Create a docker-compose file ([docker-compose.yml](docker-compose.yml))

## The Database: [SQL script](timescaleDB_SunGrow.txt)

The data is seperated into 3 main group, groupped by its logging frequencies:

1. **Log-once data**: static data that never changes

![once](once.png)

2. **Log-on-change data**: a data that stays the same, unless implemented with a change, e.g. inverter mode selection
![on_change](on_change.png)

3. **Log-every-5-minutes data**: data that always fluctuate time to time, e.g. phase A voltage

![5min](5min.png)


### Log-once data

**inverters**: a table containing static information about the inverter, e.g. serial number

### Log-on-change data
consists of three tables:

1. **inverter_work_state**: information on inverter's work state
2. **inverter_mode_selection**: inverter's switch/mode status, e.g. Power limitation switch
3. **inverter_fault_alarm**: only log if there were a fault alarm

### Log-every-5-minutes data
consists of two tables:

1. **inverter_running_time_and_energy**: culmulative data of inverter's running time and its energy produced, e.g. Daily power yield
2. **inverter_and_grid table**: real-time data of inverter (DC side), and electrical grid (AC side), e.g. Grid frequency

### TimescaleDB database
can be accessed via Docker:
1. Write a docker-compose.yml file with timescaledb in it

- create a `volume` to safely store the database

```yml
services:
  timescaledb:
    image: timescale/timescaledb:2.20.0-pg17
    ports:
      - "54321:5432"  # Expose PostgreSQL (TimescaleDB) on host port 30000
    environment:
    #Required by timescaleDB
      POSTGRES_DB: "inverter_data"
      POSTGRES_USER: "jade"
      POSTGRES_PASSWORD: "password"

    #Our own variables
      DB_NAME: "inverter_data"
      DB_USER: "jade"
      PASSWORD: "password"  # Default POSTGRES_USER: postgres, Default POSTGRES_DB: postgres
      HOST: "localhost"
      PORT: 54321

      PGTZ: "Asia/Bangkok"
      TZ: "Asia/Bangkok"
    volumes:
      - tsdb_data:/var/lib/postgresql/data

volumes:
  tsdb_data:
```
2. In Docker's terminal, cd to the folder where `docker-compose.yml` file is located, then run ```docker compose up -d```

3. Go to timescaledb's exec tab, then login using the username and password specified in `docker-compose`, in this case, Username: `postgres`, Password: `password`, run:

```
psql -d "postgres://postgres:password@localhost/postgres
```
4. Use SQL to build the database for the inverter, full script for every tables in [SQL script](timescaleDB_SunGrow.txt)
```sql
CREATE TABLE inverter_work_state (
  timestamp TIMESTAMPTZ NOT NULL,
  inverter_id INTEGER REFERENCES inverters(inverter_id) ON DELETE CASCADE,
  start_stop_control VARCHAR(30),
  work_state INTEGER,
  work_state_bitwise BIGINT,
  work_status1 INTEGER,
  work_status2 INTEGER,
  heart_beat INTEGER,
  PRIMARY KEY (timestamp)
); --this builds the inverter_work_state table, with columns and its data types as specified
```

## Modbus polling script structure

```
Project diagram
│
├── main.py
│
│
├── Utility
│   ├── db_connect.py
│   │  
│   └── decode.py 
│       
├── Polling Operations
│   ├── pollingInverterID.py
│   │   
│   ├── pollingInverterState.py 
│   │   
│   └── pollingInverterMeasurements.py
│
├── Register Mappings
│    ├── inverters.py 
│    ├── inverter_work_state.py 
│    ├── inverter_mode_selection.py 
│    ├── inverter_running_time_energy.py
│    ├── inverter_and_grid.py
│    └── inverter_fault_alarm.py
│
└── Inverter IP Mapping  
     └── inverter_ip.py

```

## Mapping Files

### Mapping for all 6 tables:

- [inverters.py](inverters.py)

- [inverter_work_state.py](inverter_work_state.py)

- [inverter_running_time_energy.py](inverter_running_time_energy.py)

- [inverter_mode_selection.py](inverter_mode_selection.py)

- [inverter_fault_alarm.py](inverter_fault_alarm.py)

- [inverter_and_grid.py](inverter_and_grid.py)

### Inverters' IP mapping: 
- [inverter_ip.py](inverter_ip.py)


**Mapping file** maps each information (each Modbus register), by table, in a form of dict, so that the polling code can use this mapping to determine which addresses to poll the data from

A mapping consists of:

1. **Name of the data (name)**
2. **Modbus address of the data (adr)**
3. **Data type (data_type)**: U16/U32/UTF-8
4. **Data scale (scale)**: multiply the raw data with this number to get the actual data
5. **Data space (space)**: 3X: read only / 4X: read and write
6. **Data size (reg_size)**

**e.g.** the mapping for the `inverters` table:
```py
inverters_mapping = [
    {"name": "protocol_num", "adr": 4950, "data_type": "U32", "scale": 1.0, "space": "3X", "reg_size": 2},
    {"name": "protocol_ver", "adr": 4952, "data_type": "U32", "scale": 1.0, "space": "3X", "reg_size": 2},
    {"name": "arm_software_ver", "adr": 4954, "data_type": "UTF-16", "scale": 1.0, "space": "3X", "reg_size": 15},
    {"name": "dsp_software_ver", "adr": 4969, "data_type": "UTF-16", "scale": 1.0, "space": "3X", "reg_size": 15},
    {"name": "serial_number", "adr": 4990, "data_type": "UTF-8", "scale": 1.0, "space": "3X", "reg_size": 10},
    {"name": "device_type_code", "adr": 5000, "data_type": "U16", "scale": 1.0, "space": "3X", "reg_size": 1},
    {"name": "nominal_active_power", "adr": 5001, "data_type": "U16", "scale": 0.1, "space": "3X", "reg_size": 1},
    {"name": "output_type", "adr": 5002, "data_type": "U16", "scale": 1.0, "space": "3X", "reg_size": 1},
    {"name": "nominal_reactive_power", "adr": 5049, "data_type": "U16", "scale": 0.1, "space": "3X", "reg_size": 1},
    {"name": "present_country", "adr": 5114, "data_type": "U16", "scale": 1.0, "space": "3X", "reg_size": 1},
    {"name": "installed_pv_power", "adr": 5016, "data_type": "U16", "scale": 0.01, "space": "4X", "reg_size": 1}
]

```


## Pymodbus Polling Files

Consists of 3 independent codes, each code polls data according to its datalogging frequency (log every 5 minutes/ log on change/ log once)

**1. Polls log-once data: [pollingInverterID.py](pollingInverterID.py)**

**2. Polls log-on-change data: [pollingInverterState.py](pollingInverterState.py)**

**3. Polls log-every-5-minutes data: [pollingInverterMeasurements.py](pollingInverterMeasurements.py)**

**Each codes consist of:** (the code below is from [pollingInverterID.py](pollingInverterID.py), which polls static data once)

### 1. Importing the necessary libraries

```py
#Importing a library that can communicate with the inverter
from pymodbus.client import ModbusTcpClient

#Importing the mapped files
from inverters import inverters_mapping

#Importing a file that decodes binary numbers
from decode import decode_binary

#Importing the cursor to pick data to and from the database
from db_connect import get_db_cursor
```

### 2. Connecting to the inverter via the inverter's IP
```py
INVERTER_IP = '192.168.100.140'
    PORT = 502

    client = ModbusTcpClient(INVERTER_IP, port=PORT)
```
### 3. Polling every single data listed in the mapping file
Create a dict 'output' to store the data extracted from the inverter

```py
output = {}
```

Iterating over every registers in [inverters.py](inverters.py)

```py
for register in master_mapping:
    name = register["name"]
    adr = register["adr"]
    data_type = register["data_type"]
    scale = register["scale"]
    space = register["space"]
    reg_size = register["reg_size"]
```

Check each data if they are 3X or 4X (they need different command)

```py
if space == "3X":# input register (read-only data) 
    data = client.read_input_registers(address=int(adr)-1, count=reg_size, slave=UNIT_ID) #the data in the selected address is extracted to the variable 'data'

elif space == "4X": #holding register (read/write data)
    data = client.read_holding_registers(address=int(adr)-1, count=reg_size, slave=UNIT_ID)
```
Store the read data in the dict 'output'

```py
output[name] = decode_binary(client, data.registers, data_type, scale)
```

Close the inverter's connection after finish polling
```py
client.close()
```

## 4. Connecting to the database

via `db_connect.py`

Write a SQL query to insert the polled data (stored in 'output' dict) in to the database, in this case, into the `inverters` table

```py
    query = """
    INSERT INTO inverters (
        inverter_id, serial_number, protocol_num, protocol_ver, 
        arm_software_ver, dsp_software_ver, device_type_code, nominal_active_power, 
        output_type, nominal_reactive_power, present_country
    )
    VALUES (
        %(inverter_id)s, %(serial_number)s, %(protocol_num)s, %(protocol_ver)s,
        %(arm_software_ver)s, %(dsp_software_ver)s, %(device_type_code)s, %(nominal_active_power)s,
        %(output_type)s, %(nominal_reactive_power)s, %(present_country)s
    )
```

Creating `db_fields` to list every values needed to insert into the database
```    
    db_fields = [
        "inverter_id", "serial_number", "protocol_num", 
        "protocol_ver", "arm_software_ver", "dsp_software_ver", "device_type_code", 
        "nominal_active_power", "output_type", "nominal_reactive_power", "present_country"
    ]
```

Executing the query, using the **cursor** from `db_connect.py `file to insert every values listed in `db_fields`

```py
with get_db_cursor() as cursor:
    cursor.execute(query, {k: output.get(k, None) for k in db_fields}) 
```

## Database Connection Establishment: [db_connect.py](db_connect.py)
Connects to the timescaledb database, so that the polled data can be stored there

### 1. Importing necessary libraries

Importing psycopg2 to establish a connection with the database, importing os to pull the database informations, such as database username, from the yaml file

```py
import psycopg2
import os
from contextlib import contextmanager
from dotenv import load_dotenv
```
### 2. Create a file named ".env"

Put it into the project's folder, and declare your database information in the file:

```txt
DB_NAME=inverter_data
DB_USER=jade
PASSWORD=password
HOST=localhost
PORT=54321
```

### 3. Declare the database's information in the variable `DB_CONFIG`

```py
load_dotenv() # loads the information from the .env file

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}
```

### 4. Connecting to the database

Below are the components in the function `get_db_cursor`

Establishing the connection to the database

```py
conn = psycopg2.connect(**DB_CONFIG)
```

Create a cursor, which is used to insert a data into the database or pick the data out of the database
```py
cursor = conn.cursor()
```
`yield` command hands the `cursor` to the code that this function, `get_db_cursor`, was imported to ([pollingInverterID.py](pollingInverterID.py), etc.), so that the cursor can insert the data in those codes into the database

```py
yield cursor
conn.commit()
```

Closing the cursor and the connection to the database after finishing polling

```py
cursor.close()
conn.close()
```

# Decoding hexadecimal values: [decode.py](decode.py)
Inverters usually store their data as a hexadecimal value, which would be more useful if they were a decimal value

**Examples**

Converting a 16-bit data (S16/U16)

```py
if data_type == "U16":
    val = client.convert_from_registers(registers, data_type=client.DATATYPE.UINT16)
```

Converting a 32-bit data (S32/U32): needs to explicitly set the word order to Little Endian, in accordance to the inverter's protocol (`word_order = "little"`)

```py
elif data_type == "U32":
    val = client.convert_from_registers(
        registers, 
        data_type=client.DATATYPE.UINT32, 
        word_order="little"  # Handles double-word little endian swapping
    )
```


Converting string data (UTF-8)

```py
    if data_type == "UTF-8":
        byte_array = bytearray()
        for reg in registers:
            byte_array.extend(reg.to_bytes(2, byteorder='big'))
        return byte_array.decode('utf-8').strip('\x00').strip()
```
## The Main Function: [polling_main.py](polling_main.py)
Assembles every Pymodbus polling files

Importing necessary files

**Thread** is a tool which allows multiple functions to run at the same time, in this case, three functions need to run at the same time: function to poll inverter's ID, inverter's state and inverter's measurements

```py
import threading #Allows the program to run multiple functions at the same time
import time 
import copy 
```

Importing every Pymodbus polling functions from the three polling files

```py
from pollingInverterID import poll_inverter_id
from pollingInverterState import poll_inverter_state_init, poll_inverter_state
from pollingInverterMeasurements import poll_inverter_measurements
```

Importing [inverter_ip.py](inverter_ip.py), to iterate over all the inverters IP
```py
from inverter_ip import inverter_ip_mapping
```

Create a Lock to ensure that the function communicates with one inverter at a time
```py
inverter_lock = threading.Lock()
```

Function to run the every-5-minute polling of inverter measurement data
```py
def run_measurements_polling(ip, port, id, UNIT_ID, lock): 
    while True:
        try:
            #lock, so the 5-sec loop waits
            with lock:
                poll_inverter_measurements(ip, port, id, UNIT_ID)
        except Exception as e:
            print(f"Error in polling inverter measurements for ip {ip}: {e}")
        
        time.sleep(5 * 60) 
```
Function to run the every-30-second polling to detect changes for the inverter state data, which needs to be logged everytime a change occurs
```py
def run_inverter_state_polling(baseline_data, ip, port, id, UNIT_ID, lock):
    baseline = copy.deepcopy(baseline_data)

    while True:
        try:
            #lock, so the 5-min loop waits
            with lock:
                poll_inverter_state(baseline, ip, port, id, UNIT_ID)
        except Exception as e:
            print(f"Error polling inverter state for ip {ip}: {e}")
        
        time.sleep(30) 
```
### `start_inverter_polling` Function

The main function used to poll every single data (log-once data, log-on-change data, log-every-5-minutes data)

Polling inverter ID (these data needs to be logged just once)

```py
poll_inverter_id(ip, port, id, UNIT_ID)
```

Running the measurement polling (whose data needs to be logged every 5 minutes), using Thread and Lock, to allow other functions to run at the same time as this

```py
t_5min = threading.Thread(
    target=run_measurements_polling,
    args=(ip, port, id, UNIT_ID, inverter_lock),
    daemon=True
)
t_5min.start()
```

Running the state data polling (polled every 30 seconds, but only log to database if there is a change), using Thread and Lock, to allow other functions to run at the same time as this
```py
t_5sec = threading.Thread(
    target=run_inverter_state_polling,
    args=(baseline_data, ip, port, id, UNIT_ID, inverter_lock),
    daemon=True
)
t_5sec.start()
```
### Poll for every inverters

Create a for-loop for every inverters, to ensure that every inverters need to go through `start_inverter_polling` function

```py
for inverter in inverter_ip_mapping:
    start_inverter_polling(inverter)
    try:
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("Polling stopped")
```

## Dockerising polling codes: [Dockerfile](Dockerfile) & [docker-compose.yml](docker-compose.yml)

1. **Creating a Dockerfile: [Dockerfile](Dockerfile)** (Place this inside the same folder where every .py files are located)

In this Dockerfile, its job is to **copy** everything inside the folder (mapping codes, polling codes, etc.) and use `main.py` to run everything

```Dockerfile
FROM python:3.11-slim

#All below this line will be rinning in the '/app' route
WORKDIR /app

COPY requirements.txt .

#Install python's requirements, as written in the .txt file
RUN pip install --no-cache-dir -r requirements.txt

#Copy the rest of the application file (everything in the folder) into the container
COPY . . 

CMD ["python", "main.py"]
```

2. **docker-compose File: [docker-compose.yml](docker-compose.yml)** 

The exactly same file as in the Database step, no changes needed

```yml
services:
  timescaledb:
    image: timescale/timescaledb:2.20.0-pg17
    ports:
      - "54321:5432"  # Expose PostgreSQL (TimescaleDB) on host port 30000
    environment:
    #Required by timescaleDB
      POSTGRES_DB: "inverter_data"
      POSTGRES_USER: "jade"
      POSTGRES_PASSWORD: "password"

    #Our own variables
      DB_NAME: "inverter_data"
      DB_USER: "jade"
      PASSWORD: "password"  # Default POSTGRES_USER: postgres, Default POSTGRES_DB: postgres
      HOST: "localhost"
      PORT: 54321

      PGTZ: "Asia/Bangkok"
      TZ: "Asia/Bangkok"
    volumes:
      - tsdb_data:/var/lib/postgresql/data

volumes:
  tsdb_data:
```

## Storage Calculation for database

Approximately 582.75 KB/ day, 207.72 MB/ year

*(Calculated based on if every registers logs value every 5 minutes)*






