import json
import requests
from .mediafactory import MediaFactory
from media_manager import Series

class SeriesFactory(MediaFactory):
	def __init__(self, api_url, api_key):
		super().__init__(api_url, api_key)
		pass

	def load_from_pvr(self, media_id = "HaveOnDisk"):
		to_return = None

		if media_id == "HaveOnDisk" or media_id == "All":
			to_return = []

			for media in self.json_from_pvr():
				if media_id == "All" or (media_id == "HaveOnDisk" and media["totalEpisodeCount"] > 0):
					new_media = Series(media["id"], self)
					new_media.load_from_json(media)
					to_return.append(new_media)

		else:
			to_return = Series(media_id, self)
			to_return.load_from_json(self.json_from_pvr(media_id))

		return to_return

	def json_from_pvr(self, series_id = "All"):
		if series_id == "All":
			return requests.get(self._api_url + "/series/" + "?apikey=" + self._api_key).json()
		else:
			return requests.get(self._api_url + "/series/" + str(series_id) + "?apikey=" + self._api_key).json()

	def update_series(self, series_id, series_data_json):
		return super()._update_media("/series/", series_id, series_data_json)

	def rescan(self, series_id):
		print ("...  sending command to rescan series...")
		command_json = {
			'name': 'RescanSeries',
			'seriesId': series_id
		}

		r = requests.post(self._api_url + "/command?apikey=" + self._api_key, data=json.dumps(command_json))