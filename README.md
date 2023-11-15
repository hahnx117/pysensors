# `pysensors`

This is a repo for a basic Raspberry Pi Docker build with the following sensors:
+ BME688
+ ADT7410
+ VEML7700
+ DPS310

These attach to the Pi via the Stemma Qwiic Hat.

## How to Deploy

Clone this repo, then create a `.env` file with the following information:

```
HOSTNAME=<hostname>
MQTT_HOST=<mqtt_host_ip>
MQTT_PORT=<mqtt_port>
MQTT_USER=<mqtt_username>
MQTT_PASSWORD=<mqtt_password>
```

To build the container,

```
docker build -t pysensors:latest .
```

and to launch the container,

```
docker-compose up -d
```