import http
import urllib

class PushoverFactory(object):
	def __init__(self, pushover_app_token, pushover_user_key):
		self._pushover_app_token = pushover_app_token
		self._pushover_user_key = pushover_user_key
		pass

	def send_pushover_message(self, title, message):
		conn = http.client.HTTPSConnection("api.pushover.net:443")
		conn.request("POST", "/1/messages.json",
		urllib.parse.urlencode({
			"token": self._pushover_app_token,
			"user": self._pushover_user_key,
			"title": title,
			"message": message
		}), { "Content-type": "application/x-www-form-urlencoded" })

		conn.getresponse()
		return
