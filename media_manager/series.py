import os

from .mediaobject import MediaObject

class Series(MediaObject):
	def __init__(self, series_id, series_factory, json_data = None):
		self._series_id = series_id
		super().__init__(series_factory, json_data)

	def load_from_pvr(self):
		json_data = self._factory.json_from_pvr(self.series_id)

		self.load_from_json(json_data)

	def load_from_json(self, json_data):
		super().load_from_json(json_data)

		self.tv_db_id = json_data["tvdbId"]

	@property
	def series_id(self):
		return self._series_id

	def _media_files_helper(self, ignore_files = []):
		if self.path is None:
			return []

		if not os.path.isdir(self.path):
			return []

		to_return = []

		for season in self.season_folders:
			season_files = [f for f in os.listdir(self.path + season) if (f.endswith('.mkv') or f.endswith('.m4v') or f.endswith('mp4'))]

			# NOTE: TV SERIES WILL RETURN THE PATH RELATIVE to self.path but will include the Season folder
			for media_file in season_files:
				to_return.append(season + media_file)

		return to_return

####
# This property will return the relative path of the Season folders
####
	@property
	def season_folders(self):
		season_folders = []

		for root, season_directories, files in os.walk(self.path):
			for season in season_directories:
				if season.find("Season") == -1:
					continue

				if season[-1] != "/":
					season_folder = season + "/"
				else:
					season_folder = season

				season_folders.append(season_folder)

		return season_folders
