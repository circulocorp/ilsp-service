import requests
import json
import pika
from classes.ilsp import Ilsp


url = os.environ["API_URL"]
rabbitmq = os.environ["RABBITMQ_URL"]
rabbit_user = "admin"
rabbit_pass = "admin123"
api_pass = "admin123"
il = Ilsp()


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
        return None


def fix_data(msg):
    events = []
    data = json.loads(msg)
    for event in data["events"]:
        mov = {}
        obj = json.loads(event)["header"]
        vehicle = get_vehicle(obj["UnitId"])
        print(obj["UnitId"])
        if vehicle is not None:
            mov["customerId"] = "189"
            mov["transportLineId"] = "7349"
            mov["ecoNumber"] = vehicle["Registration"]
            mov["plates"] = vehicle["Description"]
            mov["generatedEvent"] = 1
            mov["generatedEventDate"] = event["header"]["UtcTimestampSeconds"]
            mov["latitude"] = event["header"]["Latitude"]
            mov["longitude"] = event["header"]["Longitude"]
            mov["speed"] = event["header"]["Speed"]
            mov["heading"] = event["header"]["Direction"]
            mov["odometer"] = event["header"]["Odometer"]
            mov["battery"] = 100
            events.append(mov)
    if len(events) > 0:
        il.send_events(events)


def callback(ch, method, properties, body):
    fix_data(body)


def start(config):
    credentials = pika.PlainCredentials(rabbit_user, rabbit_pass)
    parameters = pika.ConnectionParameters(rabbitmq, 5672, '/', credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(config["queue"], durable=True)
    channel.basic_consume(config["queue"], callback, auto_ack=False)
    channel.start_consuming()


def main():
    config = read_config()
    print("Starting process "+config["name"]+" v"+config["version"])
    start(config)


if __name__ == '__main__':
    main()
