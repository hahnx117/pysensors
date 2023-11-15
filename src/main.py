import time
import board
import busio
import adafruit_adt7410
import adafruit_veml7700
import adafruit_bme680
import adafruit_dps310
import logging
import sys
import os
import socket
import paho.mqtt.client as mqtt
import datetime
import json

log = logging.getLogger()
log.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s:%(levelname)s: %(message)s", datefmt="%b %d %Y %H:%M:%S")
handler.setFormatter(formatter)
log.addHandler(handler)

mqtt_host = os.environ['MQTT_HOST']
mqtt_port = os.environ['MQTT_PORT']
mqtt_user = os.environ['MQTT_USER']
mqtt_password = os.environ['MQTT_PASSWORD']

hostname = socket.gethostname()

logging.debug("Initializing sensors.")

state_topic = f"{hostname}/sensor"
logging.debug(f"State topic: {state_topic}")

try:
    i2c = board.I2C()
except ValueError:
    logging.warning("I2C Port not initialized. Turn I2C on in raspi-config. Cannot start.")
    sys.exit()

try:
    adt = adafruit_adt7410.ADT7410(i2c, address=0x48)
    adt.high_resolution = True
except ValueError:
    logging.warning("ADT7410 not initialized. Not found at address 0x48.")
    sys.exit()

try:
    veml7700 = adafruit_veml7700.VEML7700(i2c)
except ValueError:
    logging.warning("VEML7700 not initialized. Not found at address 0x10.")
    sys.exit()

try:
    sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c)
    logging.info(f"BME688 initializes at {sensor.temperature}")
except ValueError:
    logging.warning("BME688 not initialized. Not found at address 0x77.")
    sys.exit()
except RuntimeError:
    logging.warning("BME688 and DPS310 share the same address. Solder the jumper on back to change the address.")
    sys.exit()

try:
    dps310 = adafruit_dps310.DPS310(address=0x76, i2c_bus = i2c)
    dps310.initialize()
except ValueError:
    logging.warning("DPS310 not initialized. Not found at address 0x76.")
    sys.exit()

## Take some sample readings to get the temperature offset
i = 1
logging.info("Initializing temperature.")
for i in range(1,10):
    logging.info(f"BME688 temp read {i}: {sensor.temperature}")
    time.sleep(5)
    i += 1
temperature_offset = sensor.temperature - ((adt.temperature + dps310.temperature) / 2.)
logging.info(f"Temperature offset for BME688: {temperature_offset}")

## DEFINE THE HOME ASSISTANT DISCOVERY CONFIG OBJECTS ##
## START WITH PRESSURE/TEMP/ALT, THEN LIGHT, THEN MAG/ACCEL

def register_devices_using_discovery(mqtt_client):
    """Create config objects for HA Discovery."""

    ha_discovery_root = "homeassistant/sensor"

    temp_unique_id = f"{hostname}_temp"
    humidity_unique_id = f"{hostname}_humidity"
    pressure_unique_id = f"{hostname}_pressure"
    tvoc_unique_id = f"{hostname}_tvoc"
    report_time_unique_id = f"{hostname}_report_time"
    visible_unique_id = f"{hostname}_visible"


    temp_discovery_topic = f"{ha_discovery_root}/{temp_unique_id}/config"
    humidity_discovery_topic = f"{ha_discovery_root}/{humidity_unique_id}/config"
    pressure_discovery_topic = f"{ha_discovery_root}/{pressure_unique_id}/config"
    tvoc_discovery_topic = f"{ha_discovery_root}/{tvoc_unique_id}/config"
    report_time_discovery_topic = f"{ha_discovery_root}/{report_time_unique_id}/config"
    visible_discovery_topic = f"{ha_discovery_root}/{visible_unique_id}/config"

    device_dict = {
        "identifiers": f"{hostname}_pi_zero_2_w",
        "manufacturer": "RPI Foundation + Adafruit + hahnx117",
        "name": f"Raspberry Pi Zero 2 W: {hostname}",
    }

    temp_config_object = {
        "name": "Temperature",
        "unique_id": temp_unique_id,
        "state_topic": state_topic,
        "device_class": "temperature",
        "unit_of_measurement": "°C",
        "value_template": "{{ value_json.payload.temperature | float | round(1) }}",
        "device": device_dict,
    }

    humidity_config_object = {
        "name": "Humidity",
        "unique_id": humidity_unique_id,
        "state_topic": state_topic,
        "device_class": "humidity",
        "unit_of_measurement": "%",
        "value_template": "{{ value_json.payload.humidity | float | round(1) }}",
        "device": device_dict,
    }

    pressure_config_object = {
        "name": "Pressure",
        "unique_id": pressure_unique_id,
        "state_topic": state_topic,
        "device_class": "atmospheric_pressure",
        "unit_of_measurement": "hPa",
        "value_template": "{{ value_json.payload.pressure | float | round(1) }}",
        "device": device_dict,
    }

    tvoc_config_object = {
        "name": "TVOC",
        "unique_id": tvoc_unique_id,
        "unit_of_measurement": "ohm",
        "state_topic": state_topic,
        "value_template": "{{ value_json.payload.gas | float | round(1) }}",
        "device": device_dict,
    }

    report_time_config_object = {
        "name": "Timestamp",
        "unique_id": report_time_unique_id,
        "state_topic": state_topic,
        "device_class": "timestamp",
        "value_template": "{{ value_json.payload.report_time }}",
        "device": device_dict,
    }

    visible_config_object = {
        "name": "Visible Light",
        "unique_id": visible_unique_id,
        "state_topic": state_topic,
        "device_class": "illuminance",
        "unit_of_measurement": "lx",
        "value_template": "{{ value_json.payload.visible_light | float | round(2)}}",
        "device": device_dict,
    }

    logging.info("Discovery config objects:")
    logging.info(json.dumps(temp_config_object))
    logging.info(json.dumps(humidity_config_object))
    logging.info(json.dumps(pressure_config_object))
    logging.info(json.dumps(tvoc_config_object))
    logging.info(json.dumps(report_time_config_object))
    logging.info(json.dumps(visible_config_object))

    try:
        mqtt_client.publish(temp_discovery_topic, json.dumps(temp_config_object), qos=1, retain=True)
        mqtt_client.publish(humidity_discovery_topic, json.dumps(humidity_config_object), qos=1, retain=True)
        mqtt_client.publish(pressure_discovery_topic, json.dumps(pressure_config_object), qos=1, retain=True)
        mqtt_client.publish(tvoc_discovery_topic, json.dumps(tvoc_config_object), qos=1, retain=True)
        mqtt_client.publish(report_time_discovery_topic, json.dumps(report_time_config_object), qos=1, retain=True)
        mqtt_client.publish(visible_discovery_topic, json.dumps(visible_config_object), qos=1, retain=True)
    except Exception as e:
        logging.error(e)

client = mqtt.Client()
client.username_pw_set(mqtt_user, mqtt_password)
client.connect(mqtt_host, int(mqtt_port))
client.loop_start()

if __name__ == "__main__":
    while True:
        register_devices_using_discovery(client)
        average_temp = None
        average_pressure = None
        logging.info(f"ADT7410 temperature: {adt.temperature:.2f}")
        logging.info(f"VEML7700 Ambient light: {veml7700.light:.2f}")
        logging.info(f"VEML7700 Lux: {veml7700.lux:.2f}")
        logging.info(f"Temperature offset: {temperature_offset: .2f}")
        logging.info(f"BME688 Temperature: {(sensor.temperature - temperature_offset):.2f} degrees C")
        logging.info(f"BME688 Gas: {sensor.gas:.2f} ohms")
        logging.info(f"BME688 Humidity: {sensor.humidity:.2f}%")
        logging.info(f"BME688 Pressure: {sensor.pressure:.2f}hPa")
        logging.info(f"DPS310 Temperature = {dps310.temperature:.2f} *C")
        logging.info(f"DPS310 Pressure = {dps310.pressure:.2f} hPa")
        average_temp = (adt.temperature + (sensor.temperature - temperature_offset) + dps310.temperature) / 3.
        average_pressure = (sensor.pressure + dps310.pressure) / 2.
        logging.info(f"Average temp: {average_temp: .1f}")
        logging.info(f"Average pressure: {average_pressure: .2f}")

        data_dict = {
            "topic": state_topic,
            "payload": {
                "temperature": average_temp,
                "humidity": sensor.humidity,
                "pressure": average_pressure,
                "gas": sensor.gas,
                "visible_light": veml7700.lux,
                "report_time": datetime.datetime.now().astimezone().isoformat(),
            },
            "status": "online",
        }

        sensor_payload = json.dumps(data_dict)
        logging.info("sensor_payload:")
        logging.info(sensor_payload)

        client.publish(state_topic, sensor_payload, qos=1, retain=True)

        data_dict = None

        time.sleep(15)
