var pjson = require('./package.json');
var amqp = require('amqplib/callback_api');
var request = require('request-promise');
var rest = require('sync-rest-client');
var dateFormat = require('dateformat');
var secrets = require('docker-secrets-nodejs');
var rabbitmq = process.env.RABBITMQ_URL || "192.168.1.70";
var circulocorp = process.env.CIRCULOCORP || "http://localhost:8080";
var url = process.env.URL_ILSP || "https://www.ilspservices.com.mx/CustomerServices/api/SetLastEventMassive";

var url_token = process.env.URL_TOKEN || "https://www.ilspservices.com.mx/identityserver/connect/token/";

function formatTime(time){
  var date = new Date(time).toLocaleString('en-US', { timeZone: 'America/Mexico_City' });
  var time=dateFormat(date,"yyyy-mm-ddTHH:MM:ss");
  return time;
}

function utcToDate(UtcTimestampSeconds){
    var d = new Date(0);
    d.setUTCSeconds(UtcTimestampSeconds);
    return d;
}

function getVehicle(unitid){
    var response = rest.get(circulocorp+"/api/vehicles?Unit_Id="+unitid);
    return response.body[0];
}


function getToken(msg){
   var req = request({
			"method":"POST",
			"uri": url_token,			
			"headers": {
				'Content-Type': 'application/x-www-form-urlencoded'	
			},
			"formData": {
				grant_type: 'client_credentials',
				scope: 'customers.api',
				client_id: 'customers.prod',
				client_secret: 'CustomersApi'
			}
		}).then(function(re){
			fixData(msg,JSON.parse(re));
	 });
}

function sendEvents(events, token){
  var auth = "Bearer "+token;
  request.post({
  url: url,
  headers: {
    'Authorization': auth
  },
  body: JSON.stringify(events)
  },
  function(error, response, body){
  	console.log(body);
  	console.log(response);
  	console.log(error);
  });
}

function fixData(msg, token){
	var events = [];
	var obj = JSON.parse(msg.content.toString());
    for(var i=0;i<obj["events"].length;i++){
        var event = obj["events"][i];
        var vehicle = getVehicle(event["header"]["UnitId"]);
        var mov = {};
        var codigo = 1;
        if(vehicle != null){
        	mov["customerId"]= ""
        	mov["transportLineId"] = "";
        	mov["ecoNumber"] = vehicle["Registration"];
        	mov["plates"] = vehicle["Description"];
        	mov["generatedEvent"] = codigo;
        	mov["generatedEventDate"] = formTime(utcToDate(event["header"]["UtcTimestampSeconds"]));
        	mov["latitude"] = event["header"]["Latitude"];
        	mov["longitude"] = event["header"]["Longitude"];
        	mov["speed"] = event["header"]["Speed"];
        	mov["heading"] = event["header"]["Direction"];
        	mov["odometer"] = event["header"]["Odometer"];
        	mov["battery"] = event["header"]["charge_level_percentage"] || 100;
        	events.push(mov);
        }
   }
   sendEvents(events, token["access_token"]);
}

function start(){
  console.log("Starting "+pjson.name+"  "+pjson.version);
  var rabbitmq_user = secrets.get("rabbitmq_user");
  var rabbitmq_passw = secrets.get("rabbitmq_passw");
  amqp.connect('amqp://'+rabbitmq_user+':'+rabbitmq_passw+'@'+rabbitmq, function(err, conn) {
    if(err) {
      console.log(err);
    }
    conn.createChannel(function(err, ch) {
      if(err){
        console.log(err);
      }
    var ex = 'circulocorp';
    ch.assertExchange(ex, 'direct', {durable: true});
    ch.assertQueue('ilsp', {exclusive: false}, function(err, q) {
      if(err){
        console.log(err);
      }
      ch.bindQueue(q.queue, ex, 'ilsp');
      ch.consume(q.queue, getToken, {noAck: true});
    });

  });
  });
}

getToken("Mensaje");
//start();