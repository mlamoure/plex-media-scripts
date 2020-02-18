import os
from pymediainfo import MediaInfo

from .core import *

class MediaObject(object):
	def __init__(self, factory):
		self._factory = factory

	def __eq__(self, other):
		if type(other) is type(self):
			return self.media_id == other.media_id
		elif isinstance(other, str):
			if self.imdb is not None:
				return self.imdb == other

			# Should add other methods of comparison

		return False

	@property
	def path(self):
		if self._path[-1] != "/":
			return self._path + "/"

		return self._path
	
	@property
	def title(self):
		return self._title

	@property
	def json(self):
		if self._json["path"] != self.path:
			self._json["path"] = self.path

		return self._json

	@property
	def media_files(self):
		if self.path is None:
			return None

		if not os.path.isdir(self.path):
			return None

		if not hasattr(self, "_media_files"):
			ignore_files = ["-behindthescenes", "-deleted", "-featurette", "-interview", "-scene", "-short", "-trailer", "-other"]

			self._media_files = [f for f in os.listdir(self.path) if (f.endswith('.mkv') or f.endswith('.m4v') or f.endswith('mp4')) and not any(ele in f for ele in ignore_files)]

		return self._media_files
	
	def best_rip_type(self):
		if len(self.remux_files) > 0:
			return RIPType.REMUX
		elif len(self.webdl_files) > 0:
			return RIPType.WEBDL
		elif len(self.webrip_files) > 0:
			return RIPType.WEBRIP

		return None

	@property
	def resolution(self):
		if len(self.files_2160p) > 0:
			return RESOLUTION.UHD
		elif len(self.files_1080p) > 0:
			return RESOLUTION.FULLHD
		elif len(self.files_720p) > 0:
			return RESOLUTION.HD720

		return None
	
	
	def load_media_stats(self):
		file_count = 0
		media_files_stats = []

		if self.media_files is None:
			return

		for media_file in self.media_files:
			full_path_media_file = self.path + media_file
			media_info = MediaInfo.parse(full_path_media_file)
			file_size = os.path.getsize(full_path_media_file)
			file_count = file_count + 1
			track_count = 0
			track_highest_resolution = 0

#			print("    File " + str(file_count) + ": " + str(media_file))
#			print("        file size: " + str(convert_size(file_size)))

			for track in media_info.tracks:
				track_count = track_count + 1
				if track.track_type == 'Video':

					video_track_resolution = int(track.height)
					video_track_bit_rate = track.bit_rate

					if video_track_resolution > track_highest_resolution:
						track_highest_resolution = video_track_resolution

			movie_rip_type = None
			if media_file.lower().find("webrip") > 0:
				movie_rip_type = RIPType.WEBRIP
			elif media_file.lower().find("web-dl") > 0:
				movie_rip_type = RIPType.WEBDL
			elif media_file.lower().find("remux") or media_file.lower().find("bluray"):
				movie_rip_type = RIPType.REMUX

#			print ("file resolution: " + str(track_highest_resolution) + ", RIP Type: " + str(movie_rip_type))

			media_files_stats.append([full_path_media_file, media_file, track_highest_resolution, movie_rip_type])

		self._files_720p = [f for f in media_files_stats if f[2] > 480 and f[2] <= 720]
		self._files_1080p = [f for f in media_files_stats if f[2] > 720 and f[2] <= 1080]
		self._files_2160p = [f for f in media_files_stats if f[2] >= 2160]

		self._webrip_files = [f for f in media_files_stats if f[3] == RIPType.WEBRIP]
		self._webdl_files = [f for f in media_files_stats if f[3] == RIPType.WEBDL]
		self._remux_files = [f for f in media_files_stats if f[3] == RIPType.REMUX]

#		self.sdr_4k_files = [f for f in media_files_stats if f[2] >= 2160 and str(f[1]).lower().find("sdr") > 0]
		self._sdr_4k_files = []
		for f in media_files_stats:
			if f[1].lower().find(".sdr.") > 0:
				self._sdr_4k_files.append(f)

	def load_from_json(self, json_data):
		self._json = json_data

		self._title = json_data["title"]
		self._path = json_data["path"]

		if "imdbId" in json_data:
			self._imdb = json_data["imdbId"]

	def update_path(self, new_path):
		self._path = new_path

		self._factory.update_series(self.media_id, self.json)		

	@property
	def files_720p(self):
		if not hasattr(self, "_files_720p"):
			self.load_media_stats()

		return self._files_720p

	@property
	def files_1080p(self):
		if not hasattr(self, "_files_1080p"):
			self.load_media_stats()

		return self._files_1080p

	@property
	def files_2160p(self):
		if not hasattr(self, "_files_2160p"):
			self.load_media_stats()

		return self._files_2160p

	@property
	def webrip_files(self):
		if not hasattr(self, "_webrip_files"):
			self.load_media_stats()

		return self._webrip_files

	@property
	def webdl_files(self):
		if not hasattr(self, "_webdl_files"):
			self.load_media_stats()

		return self._webdl_files

	@property
	def sdr_4k_files(self):
		if not hasattr(self, "_sdr_4k_files"):
			self.load_media_stats()

		return self._sdr_4k_files

	@property
	def remux_files(self):
		if not hasattr(self, "_remux_files"):
			self.load_media_stats()

		return self._remux_files
	
	@property
	def imdb(self):
		if hasattr(self, "_imdb"):
			return self._imdb

		return None
	
	@property
	def media_id(self):
		if hasattr(self, "series_id"):
			return self.series_id
		elif hasattr(self, "movie_id"):
			return self.movie_id
	
	def rescan(self):
		self._factory.rescan(self.media_id)