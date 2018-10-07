import requests
from datetime import datetime, timedelta


class Ilsp(object):

    def __init__(self, client_secret):
        self._token = {}
        self._secret = client_secret
        self._urlsend = "https://www.ilspservices.com.mx/CustomerServices/api/SetLastEventMassive"
        self.set_token()

    def set_token(self):
        #BrJFksd5psTT
        url = "https://www.ilspservices.com.mx/identityserver/connect/token/"
        data = {'grant_type': 'client_credentials', 'client_id': 'supplier.circulocorp',
                'client_secret': self._secret, 'scope': 'customers.api'}
        resp = requests.post(url, data=data)
        if resp.status_code == 200:
            token = resp.json()
            valid = datetime.now() + timedelta(seconds=int(token["expires_in"]))
            token["valid_until"] = valid.__str__()
            self._token = token
        else:
            print(resp.content)

    def check_token(self):
        if not self._token:
            return False
        else:
            valid_until = datetime.strptime(self._token["valid_until"], '%Y-%m-%d %H:%M:%S.%f')
            now = datetime.now()
            if now > valid_until:
                return False
            else:
                return True

    def send_events(self, events):
        if not self.check_token():
            self.set_token()
        print(events)





