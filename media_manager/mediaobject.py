import os
import datetime 
from pathlib import Path
import shutil

from pymediainfo import MediaInfo

from .core import *

class MediaObject(object):
	def __init__(self, factory, json_data = None):
		self._factory = factory

		if json_data is None:
			self.load_from_pvr()
		else:
			self.load_from_json(json_data)

	def __eq__(self, other):
		is_match = False

		if type(other) is type(self):
			is_match = self.media_id == other.media_id
		elif isinstance(other, str):
			## This is likely IMDB
			if not is_match and self.imdb is not None:
				is_match = self.imdb == other

		elif isinstance(other, int):
			# This is for TVDB or TheMovieDB
			if not is_match and hasattr(self, "tv_db_id"):
				is_match = self.tv_db_id == other

			if not is_match and hasattr(self, "movie_db_id"):
				is_match = self.movie_db_id == other

		return is_match

	def __getattr__(self, name):
		media_stat_properties = ["files_720p", "files_1080p", "files_2160p", "webrip_files", "webdl_files", "sdr_4k_files", "remux_files"]
		if any(attr in name for attr in media_stat_properties):
#			print("calling to load the media stats for media object '" + self.title + "', trigger attribute: " + name)
			self.load_media_stats()
			return getattr(self, name)

#		print ("AttributeError on: " + name)
		raise AttributeError

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

	@property
	def public_db_id(self):
		if hasattr(self, "series_id"):
			return self.tv_db_id
		elif hasattr(self, "movie_id"):
			return self.movie_db_id

	@property
	def pvr_is_available(self):
		return self._pvr_is_available
	
	@property
	def path(self):
		if self._path[-1] != "/":
			return self._path + "/"

		return self._path
	
	@property
	def title(self):
		return self._title

	@property
	def ideal_folder_name(self):
		return self.title.replace(":", "") + " (" + str(self.year) + ")"
	
	@property
	def json(self):
		if self._json["path"] != self.path:
			self._json["path"] = self.path

		return self._json

	@property
	def media_files(self):
		if hasattr(self, "movie_id"):
			ignore_files = ["-behindthescenes", "-deleted", "-featurette", "-interview", "-scene", "-short", "-trailer", "-other"]
		else:
			ignore_files = []

		return self._media_files_helper(ignore_files)

	@property
	def all_media_files(self):
		return self._media_files_helper()
	
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

#		print ("loading media stats for media '" + self.title + "'")
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

		self.files_720p = [f for f in media_files_stats if f[2] > 480 and f[2] <= 720]
		self.files_1080p = [f for f in media_files_stats if f[2] > 720 and f[2] <= 1080]
		self.files_2160p = [f for f in media_files_stats if f[2] > 1080]

		self.webrip_files = [f for f in media_files_stats if f[3] == RIPType.WEBRIP]
		self.webdl_files = [f for f in media_files_stats if f[3] == RIPType.WEBDL]
		self.remux_files = [f for f in media_files_stats if f[3] == RIPType.REMUX]

#		self.sdr_4k_files = [f for f in media_files_stats if f[2] >= 2160 and str(f[1]).lower().find("sdr") > 0]
		self.sdr_4k_files = []
		for f in media_files_stats:
			if f[1].lower().find(".sdr.") > 0:
				self.sdr_4k_files.append(f)

	def load_from_json(self, json_data):
		self._json = json_data

		self._title = json_data["title"]
		self._path = json_data["path"]

		if "isAvailable" in json_data:
			self._pvr_is_available = json_data["isAvailable"]

		self.pvr_size_on_disk = json_data["sizeOnDisk"]
		self.year = json_data["year"]

		self.pvr_media_files = []
		if "movieFile" in json_data:
#			for file in json_data["movieFile"]:
			self.pvr_media_files.append(self.path + json_data["movieFile"]["relativePath"])
	
		if "physical_release" in json_data:
			self.physical_release = datetime.datetime.strptime(json_data["physicalRelease"], '%Y-%m-%dT%H:%M:%SZ')
		else:
			self.physical_release = "unknown"


		if "imdbId" in json_data:
			self._imdb = json_data["imdbId"]

	def move_media_files(self, new_path):
		print ()
		print ("Attempting to move media files from " + self.path + " to " + new_path + ".")

		if not os.path.isdir(new_path):
			print ("          could not move media files because the path does not exist.")
			return

		if len(self.all_media_files) == 0:
			print ("          no relavent media files to move.")
			return

		if hasattr(self, "season_folders"):
			## Need to move the season folders first....
			for season_folder in self.season_folders:
				new_season_path = new_path + season_folder

				if not os.path.isdir(new_season_path):
					print ("          creating Season folder: " + new_season_path)
					os.mkdir(new_season_path)
				else:
					print ("          skipping creating season folder because it already exists: " + new_season_path)

		## Then need to move each of the files...
		for media_file in self.all_media_files:
			to_move_file_name = os.path.basename(media_file)
			to_move_season_folder = ""
			if hasattr(self, "season_folders"):
				for season_folder in self.season_folders:
					if media_file.find(season_folder) >= 0:
						to_move_season_folder = season_folder
						break

				# We could not find the season folder for the media file.... strange.  Log it.
				if len(to_move_season_folder) == 0:
					print("          Could not identify the Season for file: " + media_file)
					continue

			new_file_path = new_path + to_move_season_folder + to_move_file_name 

			print ("          moving file " + media_file + " to " + new_file_path + ".")
			os.replace(self.path + media_file, new_file_path)

		if len(self.all_media_files) == 0:
			print ("          sucessfully moved all media files from " + self.path + " to " + new_path + ".  Now deleting the empty directory")

			### Need to do this recursively.
			shutil.rmtree(self.path)

	def update_path(self, new_path):
		self._path = new_path

		assert (new_path.find("Season") == -1)

		self._factory.update_media(self.media_id, self.json)