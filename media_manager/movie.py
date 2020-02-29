import os

from .mediaobject import MediaObject

class Movie(MediaObject):
	def __init__(self, movie_id, movie_factory, json_data = None):
		self._movie_id = movie_id
		super().__init__(movie_factory, json_data)

	def load_from_pvr(self):
		json_data = self._factory.json_from_pvr(self.movie_id)

		self.load_from_json(json_data)

	def load_from_json(self, json_data):
		super().load_from_json(json_data)

		self.movie_db_id = json_data["tmdbId"]

	def _media_files_helper(self, ignore_files = []):
		if self.path is None:
			return []

		if not os.path.isdir(self.path):
			return []

		return [f for f in os.listdir(self.path) if (f.endswith('.mkv') or f.endswith('.m4v') or f.endswith('mp4')) and not any(ele in f for ele in ignore_files)]
		
	@property
	def movie_id(self):
		return self._movie_id		