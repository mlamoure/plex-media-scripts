import json
import requests

from .mediafactory import MediaFactory
from media_manager import Movie
from .core import *


class MovieFactory(MediaFactory):
	def __init__(self, api_url, api_key):
		super().__init__(api_url, api_key)

	def update_series(self, movie_id, movie_data_json):
		return super()._update_media("/movie/", movie_id, movie_data_json)

	def json_from_pvr(self, movie_id = "All"):
		if movie_id == "All":
			return requests.get(self._api_url + "/movie/" + "?apikey=" + self._api_key).json()
		else:
			return requests.get(self._api_url + "/movie/" + str(movie_id) + "?apikey=" + self._api_key).json()

	def load_from_pvr(self, media_id = "HaveOnDisk"):
		if media_id == "HaveOnDisk" or media_id == "All":
			to_return = []

			for media in self.json_from_pvr():
				if media_id == "All" or (media_id == "HaveOnDisk" and media["hasFile"]):
					new_media = Movie(media["id"], self)
					new_media.load_from_json(media)
					to_return.append(new_media)
		else:
			to_return = Movie(media_id, self)
			to_return.load_from_json(self.json_from_pvr(media_id))

		return to_return

	def rescan(self, movie_id):
		print ("    sending command to rescan series...")
		command_json = {
			'name': 'RescanSeries',
			'movieId': movie_id
		}

		r = requests.post(self._api_url + "/command?apikey=" + self._api_key, data=json.dumps(command_json))

	def remove_extra_movie_files(self, movie, pushover = None, verbose = True):
		single_line_stat = ""
		if verbose:
			print ()
			print ("Looking at the files currently in the plex directory for movie: " + movie.title)
			print ()
			print ("    Summary of Movie Files: ")	
			print ("        720p versions: " + str(len(movie.files_720p)) + ", files: " + str([f[0] for f in movie.files_720p]))
			print ("        1080p versions: " + str(len(movie.files_1080p)) + ", files: " + str([f[0] for f in movie.files_1080p]))
			print ("        4K versions: " + str(len(movie.files_2160p)) + ", files: " + str([f[0] for f in movie.files_2160p]))
			print ("        4K SDR versions: " + str(len(movie.sdr_4k_files)) + ", files: " + str([f[0] for f in movie.sdr_4k_files]))
			print ()
			print ("        WEB-RIP versions: " + str(len(movie.webrip_files)) + ", files: " + str([f[0] for f in movie.webrip_files]))
			print ("        WEB-DL versions: " + str(len(movie.webdl_files)) + ", files: " + str([f[0] for f in movie.webdl_files]))
			print ("        REMUX versions: " + str(len(movie.remux_files)) + ", files: " + str([f[0] for f in movie.remux_files]))
		else:
			single_line_stat = "720p versions: " + str(len(movie.files_720p)) + ", 1080p versions: " + str(len(movie.files_1080p)) + ", 4K versions: " + str(len(movie.files_2160p)) + ", 4K SDR versions: " + str(len(movie.sdr_4k_files)) + ", WEB-RIP versions: " + str(len(movie.webrip_files)) + ", WEB-DL versions: " + str(len(movie.webdl_files)) + ", REMUX versions: " + str(len(movie.remux_files))

		if len(movie.media_files) > 1:
			if verbose:
				print ()
				print ("Reviewing auto-removal rules since there are multiple copies of the same movie:")

			if len(movie.files_720p) == 1 and (len(movie.files_1080p) >= 1 or len(movie.files_2160p) >= 1):
				movie_to_delete = movie.files_720p[0][0]

				if pushover is not None:
					pushover.SendPushoverMessage("Multiple files for same movie found", "Deleting a 720p version of movie " + movie.title + ".  Location: " + movie_to_delete)
	
				print("        Multiple files for same movie were found.  Deleting a 720p version of movie " + movie.title + ".  Location: " + movie_to_delete)
				os.remove(movie_to_delete)

			elif len(movie.files_1080p) > 2 and len(movie.webrip_files) == 1:
				movie_to_delete = movie.webrip_files[0][0]

				if pushover is not None:
					pushover.SendPushoverMessage("Multiple files for same movie found", "Two or more 1080p copies were found.  Deleting a Web-RIP version of movie " + movie.title + ".  Location: " + movie_to_delete)
	
				print("        Two or more 1080p copies of the same movie were found.  Deleting a Web-RIP version of movie " + movie.title + ".  Location: " + movie_to_delete)
				os.remove(movie_to_delete)

			elif len(movie.files_2160p) >= 2 and movie.files_1080p == 1:
				movie_to_delete = movie.files_1080p[0][0]

				if pushover is not None:
					pushover.SendPushoverMessage("Multiple files for same movie found", "Two or more 4K copies were found.  Deleting the older 1080p version of movie " + movie.title + ".  Location: " + movie_to_delete)
	
				print("        Two or more 4K copies of the same movie were found.  Deleting the older 1080p version of movie " + movie.title + ".  Location: " + movie_to_delete)
				os.remove(movie_to_delete)

			elif len(movie.files_2160p) == 1 and len(movie.files_1080p) == 1 and len(movie.sdr_4k_files) == 1:
				movie_to_delete = movie.files_1080p[0][0]

				if pushover is not None:
					pushover.SendPushoverMessage("Multiple files for same movie found", "A 4K SDR and 1080p copy of the same movie were found.  Deleting the older 1080p version of movie " + movie.title + ".  Location: " + movie_to_delete)
	
				print("        A 4K SDR and 1080p copy of the same movie were found.  Deleting the older 1080p version of movie " + movie.title + ".  Location: " + movie_to_delete)
				os.remove(movie_to_delete)

			else:
				print ("        " + str(len(movie.media_files)) + " files for movie '" + movie.title + "' were found, but no recommendation to remove any versions at this time.  " + single_line_stat)
