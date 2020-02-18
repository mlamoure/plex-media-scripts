from .mediaobject import MediaObject

class Series(MediaObject):
	def __init__(self, series_id, series_factory):
		super().__init__(series_factory)

		self._series_id = series_id

		self.load_from_pvr()

	def load_from_pvr(self):
		json_data = self._factory.json_from_pvr(self.series_id)

		self.load_from_json(json_data)

	def load_from_json(self, json_data):
		super().load_from_json(json_data)

	@property
	def series_id(self):
		return self._series_id