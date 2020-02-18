from .mediaobject import MediaObject

class Movie(MediaObject):
	def __init__(self, movie_id, movie_factory):
		super().__init__(movie_factory)

		self._movie_id = movie_id

		self.load_from_pvr()
#		self.load_media_stats()

	def load_from_pvr(self):
		json_data = self._factory.json_from_pvr(self.movie_id)

		self.load_from_json(json_data)

	def load_from_json(self, json_data):
		super().load_from_json(json_data)

	@property
	def movie_id(self):
		return self._movie_id		