import json
import requests
from .mediafactory import MediaFactory
from media_manager import Series

class SeriesFactory(MediaFactory):
	def __init__(self, api_url, api_key):
		super().__init__(api_url, api_key)
		pass

	def load_from_pvr(self, media_id = "haveondisk"):
		media_id = media_id.lower()

		if not hasattr(self, "__pvr_db"):
			self.__pvr_db = {}

		if str(media_id) in self.__pvr_db:
#			print ("returning series from cache for key '" + str(media_id) + "'")
			return self.__pvr_db[str(media_id)]

		if media_id == "haveondisk" or media_id == "all":
			to_return = []

			for media in self.json_from_pvr():
				if media_id == "all" or (media_id == "haveondisk" and media["hasFile"]):
					new_media = Series(media["id"], self, media)
					to_return.append(new_media)
		else:
			to_return = Series(media_id, self)

		self.__pvr_db[str(media_id)] = to_return
		return to_return

	def json_from_pvr(self, series_id = "All"):
		if series_id == "All":
			return requests.get(self._api_url + "/series/" + "?apikey=" + self._api_key).json()
		else:
			return requests.get(self._api_url + "/series/" + str(series_id) + "?apikey=" + self._api_key).json()

	def update_media(self, series_id, series_data_json):
		return super()._update_media("/series/", series_id, series_data_json)

	def rescan(self, series_id):
		print ()
		print ("sending command to rescan series...")
		command_json = {
			'name': 'RescanSeries',
			'seriesId': series_id
		}

		r = requests.post(self._api_url + "/command?apikey=" + self._api_key, data=json.dumps(command_json))