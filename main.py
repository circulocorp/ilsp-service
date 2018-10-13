import requests
import json
import pika
import os
import sys
from PydoNovosoft.utils import Utils
import json_logging
import logging
from classes.ilsp import Ilsp


json_logging.ENABLE_JSON_LOGGING = True
json_logging.init()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logpath = os.path.join('logs', 'ilsp.log')
logger.addHandler(logging.FileHandler(filename=logpath, mode='w'))
logger.addHandler(logging.StreamHandler(sys.stdout))
url = os.environ["API_URL"]
rabbitmq = os.environ["RABBITMQ_URL"]


def get_secret(secret):
    f = open('/run/secrets/'+secret).read().rstrip('\n')
    return f


def read_config():
    data = {}
    with open('package.json') as f:
        data = json.load(f)
    return data


def get_vehicle(unit_id):
    response = requests.get(url+"/api/vehicles?Unit_Id="+unit_id)
    vehicles = response.json()
    if len(vehicles) > 0:
        return vehicles[0]
    else:
        logger.error("Vehicle not found", extra={'props': {"vehicle": unit_id, "app": "ilsp", "label": "ilsp"}})
        return None


ilsp_secret = get_secret("ilsp_secret")
il = Ilsp(client_secret=ilsp_secret)


def fix_data(msg):
    events = []
    data = json.loads(msg)
    for event in data["events"]:
        mov = dict()
        obj = event["header"]
        vehicle = get_vehicle(obj["UnitId"])
        if vehicle is not None:
            mov["customerId"] = 189
            mov["transportLineId"] = 7349
            mov["ecoNumber"] = vehicle["Registration"]
            mov["plates"] = vehicle["Description"]
            mov["generatedEvent"] = 1
            mov["generatedEventDate"] = Utils.utc_to_date(event["header"]["UtcTimestampSeconds"])
            mov["latitude"] = event["header"]["Latitude"]
            mov["longitude"] = event["header"]["Longitude"]
            mov["speed"] = event["header"]["Speed"]
            mov["heading"] = event["header"]["Direction"]
            mov["odometer"] = event["header"]["Odometer"]
            mov["battery"] = 100
            events.append(mov)

    if len(events) > 0:
        resp = il.send_events(events)
        if "error" in resp:
            logger.error("There was a problem sending events to ILSP",
                         extra={'props': {"raw": resp, "app": "ilsp", "label": "ilsp"}})
        else:
            logger.info("Response from ILSP was ok",
                        extra={'props': {"raw": resp, "app": "ilsp", "label": "ilsp"}})
    else:
        logger.info("Nothing to send", extra={'props': {"app": "ilsp", "label": "ilsp"}})


def callback(ch, method, properties, body):
    logger.info("Reading message", extra={'props': {"raw": body, "app": "ilsp", "label": "ilsp"}})
    fix_data(body)


def start(config):
    rabbit_user = get_secret("rabbitmq_user")
    rabbit_pass = get_secret("rabbitmq_passw")
    credentials = pika.PlainCredentials(rabbit_user, rabbit_pass)
    parameters = pika.ConnectionParameters(rabbitmq, 5672, '/', credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(config["queue"], durable=True)
    channel.basic_consume(callback, config["queue"], no_ack=True)
    logger.info("Connection successful to RabbitMQ", extra={'props': {"app": "ilsp", "label": "ilsp"}})
    channel.start_consuming()


def main():
    print(Utils.print_title("package.json"))
    start(Utils.read_config("package.json"))


if __name__ == '__main__':
    main()
