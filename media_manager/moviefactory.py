import json
import requests
import os
from fuzzywuzzy import fuzz
from pathlib import Path

from .mediafactory import MediaFactory
from media_manager import Movie
from .core import *

class MovieFactory(MediaFactory):
	def __init__(self, api_url, api_key):
		super().__init__(api_url, api_key)

	def update_media(self, movie_id, movie_data_json):
		return super()._update_media("/movie/", movie_id, movie_data_json)

	def json_from_pvr(self, movie_id = "All"):
		if movie_id == "All":
			return requests.get(self._api_url + "/movie/" + "?apikey=" + self._api_key).json()
		else:
			return requests.get(self._api_url + "/movie/" + str(movie_id) + "?apikey=" + self._api_key).json()

	def load_from_pvr(self, media_id = "haveondisk"):
		media_id = media_id.lower()

		if not hasattr(self, "__pvr_db"):
			self.__pvr_db = {}

		if str(media_id) in self.__pvr_db:
#			print ("returning movies from cache for key '" + str(media_id) + "'")
			return self.__pvr_db[str(media_id)]

		if media_id == "haveondisk" or media_id == "all":
			to_return = []

			for media in self.json_from_pvr():
				if media_id == "all" or (media_id == "haveondisk" and media["hasFile"]):
					new_media = Movie(media["id"], self, media)
					to_return.append(new_media)
		else:
			to_return = Movie(media_id, self)

		self.__pvr_db[str(media_id)] = to_return
		return to_return

	def rescan(self, movie_id):
		print()
		print ("sending command to rescan movie...")
		command_json = {
			'name': 'RescanMovie',
			'movieId': movie_id
		}

		r = requests.post(self._api_url + "/command?apikey=" + self._api_key, data=json.dumps(command_json))

	def scan_for_duplicates(self, movie = None, pushover = None, verbose = True, is_test = False):

		print ()

		if movie is not None:
			movies = [movie]
			print ("######## Duplicate Movie Scan ########")
		else:
			movies = self.load_from_pvr("HaveOnDisk")
			print ("######## (Full Disk) Duplicate Movie Scan ########")
		
		for movie in movies:
			single_line_stat = ""
			if verbose:
				print ()
				print ("Looking at the files currently in the plex directory for movie: " + movie.title)
				print ()
				print ("    Summary of Movie Files: ")	
				print ("        720p versions: " + str(len(movie.files_720p)) + ", files: " + str([f[0] for f in movie.files_720p]))
				print ("        1080p versions: " + str(len(movie.files_1080p)) + ", files: " + str([f[0] for f in movie.files_1080p]))
				print ("        4K versions (inc. SDR and HDR): " + str(len(movie.files_2160p)) + ", files: " + str([f[0] for f in movie.files_2160p]))
				print ("        4K SDR versions: " + str(len(movie.sdr_4k_files)) + ", files: " + str([f[0] for f in movie.sdr_4k_files]))
				print ()
				print ("        WEB-RIP versions: " + str(len(movie.webrip_files)) + ", files: " + str([f[0] for f in movie.webrip_files]))
				print ("        WEB-DL versions: " + str(len(movie.webdl_files)) + ", files: " + str([f[0] for f in movie.webdl_files]))
				print ("        REMUX versions: " + str(len(movie.remux_files)) + ", files: " + str([f[0] for f in movie.remux_files]))
			else:
				single_line_stat = "\n                720p versions: " + str(len(movie.files_720p)) + ", 1080p versions: " + str(len(movie.files_1080p)) + ", 4K (HDR and SDR) versions: " + str(len(movie.files_2160p)) + ", 4K SDR versions: " + str(len(movie.sdr_4k_files)) + "\n                WEB-RIP versions: " + str(len(movie.webrip_files)) + ", WEB-DL versions: " + str(len(movie.webdl_files)) + ", REMUX versions: " + str(len(movie.remux_files))

			if len(movie.media_files) > 1:
				movie_to_delete = None
				if verbose:
					print ()
					print ("Reviewing auto-removal rules since there are multiple copies of the same movie:")

				if len(movie.files_720p) == 1 and (len(movie.files_1080p) >= 1 or len(movie.files_2160p) >= 1):
					movie_to_delete = movie.files_720p[0][0]
					log_message = "Multiple files for same movie '" + movie.title + "' were found." + single_line_stat + "\nACTION TAKEN: Deleting a 720p version, location: " + movie_to_delete

				elif len(movie.files_1080p) >= 2 and len(movie.webrip_files) == 1:
					movie_to_delete = movie.webrip_files[0][0]
					log_message = "Two or more 1080p copies of the same movie '" + movie.title + "' were found." + single_line_stat + "\nACTION TAKEN: Deleting a Web-RIP version, Location: " + movie_to_delete

				elif len(movie.files_1080p) >= 2 and len(movie.webdl_files) == 1 and len(movie.remux_files) == 1:
					movie_to_delete = movie.webdl_files[0][0]
					log_message = "Two or more 1080p copies of the same movie '" + movie.title + "' were found." + single_line_stat + "\nACTION TAKEN: Deleting a Web-DL version, Location: " + movie_to_delete

				elif len(movie.files_2160p) >= 2 and movie.files_1080p == 1:
					movie_to_delete = movie.files_1080p[0][0]
					log_message = "Two or more 4K copies of the same movie '" + movie.title + "' were found." + single_line_stat + "\nACTION TAKEN: Deleting the older 1080p version, Location: " + movie_to_delete

				elif len(movie.files_2160p) == 1 and len(movie.files_1080p) == 1 and len(movie.sdr_4k_files) == 1:
					movie_to_delete = movie.files_1080p[0][0]

					log_message = "A 4K SDR and 1080p copy of the same movie '" + movie.title + "' were found." + single_line_stat + "\nACTION TAKEN: Deleting the older 1080p version, Location: " + movie_to_delete
				else:
					print ("        " + str(len(movie.media_files)) + " files for movie '" + movie.title + "' were found, no recommendation to remove any versions.  " + single_line_stat)

				if not is_test and movie_to_delete is not None:
					os.remove(movie_to_delete)
					print (log_message)

					if pushover is not None:
						pushover.send_pushover_message("Media Manager", log_message)

		print ("     Duplicate scan complete...")


	def pvr_to_disk_validation(self, pushover = None, is_test = False):
		at_least_one_issue = False
		print ("######## PVR (Radarr) to disk validation ########")
		pvr_movies = self.load_from_pvr("All")

		## FIRST WE CHECK ALL THE PVR Entries to see if they match disk.
		for movie in pvr_movies:

			if len(movie.pvr_media_files) != len(movie.media_files):
			
				# NOTE: RADARR does not support > 1 file for a movie, so we ignore the case where PVR is 1 and actual is > 1
				if not (len(movie.pvr_media_files) == 1 and len(movie.media_files) > 1):
					at_least_one_issue = True

					print ("Movie '" + movie.title + "'" + " year: " + str(movie.year) + " has a mismatch on PVR vs on disk")
					print ("    PVR shows file count of: " + str(len(movie.pvr_media_files)) + ", files actually on disk: " + str(len(movie.media_files)))

					### MOVIE FOLDER DOES NOT HAVE THE YEAR (INCOMPATIBLE WITH RADARR NAMING CONVENTIONS)
					### This happens when the folder in Radarr is CORRECT but doesnt contain the year, so the files are not being recognized
					if not movie.path.find(str(movie.year)) > 0:
						super().rename_path_on_disk(matched_movie[0], movie.path, pushover = pushover, is_test = is_test)
					else:
						movie.rescan()

		if not at_least_one_issue:
			print ("    everything looks fine...")

		print ()
