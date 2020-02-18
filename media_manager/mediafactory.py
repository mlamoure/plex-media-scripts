import requests
import json

class MediaFactory(object):
	def __init__(self, api_url, api_key):
		self._api_url = api_url
		self._api_key = api_key
		pass

	def _update_media(self, api_path, media_id, new_json_data):
		success_confirmation = False
		r = requests.put(self._api_url + api_path + str(media_id) + "?apikey=" + self._api_key, data=json.dumps(new_json_data))

		if r.json()["id"] == media_id:
			success_confirmation = True

		return success_confirmation		