import requests
import json
import os
from fuzzywuzzy import fuzz
from pathlib import Path

from .core import *

class MediaFactory(object):
	def __init__(self, api_url, api_key):
		self._api_url = api_url
		self._api_key = api_key
		pass

	def _update_media(self, api_path, media_id, new_json_data):
		success_confirmation = False
		r = requests.put(self._api_url + api_path + str(media_id) + "?apikey=" + self._api_key, data=json.dumps(new_json_data))

		try:
			success_confirmation = r.json()["id"] == media_id
		except:
			return False

		return success_confirmation

	def is_illegal_path_title(self, path):
		if path.find(":") >= 0:
			return True

		return False

	def rename_path_on_disk(self, media, full_path_old_media_folder, new_path = None, pushover = None, is_test = False):
		path = Path(full_path_old_media_folder)

		if new_path is None or self.is_illegal_path_title(new_path):
			new_path = str(path.parent) + "/" + media.ideal_folder_name + "/"

		if not os.path.isdir(new_path) and new_path != full_path_old_media_folder:
			print ("     renaming the media directory")
			print ("     current path: " + full_path_old_media_folder)
			print ("     moving to path: " + new_path)

			if not is_test:
				os.rename(full_path_old_media_folder, new_path)
				media.update_path(new_path)
		else:
			print ("     can not create a correct directory as it already exists!")

		media.rescan()
		if not pushover is None:
			pushover.send_pushover_message("Media Manager", "The Media Manager made updates to the movie locations.  Please check the email log")

	def disk_to_db_validation(self, root_folder, media_type, pushover = None, is_test = False):
		at_least_one_issue = False
		minimum_simularity_ratio = 86

		media = self.load_from_pvr("All")

		if media_type == DownloadType.MOVIE:
			pvr = "Radarr"
		elif media_type == DownloadType.EPISODE:
			pvr = "Sonarr"

		print ("######## Disk to PVR validation (" + pvr + ") ########")

		if root_folder[-1] != "/":
			root_folder = root_folder + "/"

		ignore_directories = [".grab", "@eaDir"]

		#######
		# Check all the plex folders to see if they match back with the PVR
		#####
		folders = [ name for name in os.listdir(root_folder) if os.path.isdir(os.path.join(root_folder, name)) ]

		for media_folder in folders:

			# ignore certain directores
			if any(attr in media_folder for attr in ignore_directories):
				continue

			full_path_folder = root_folder + media_folder + "/"
			matched_media = [media_item for media_item in media if media_item.path == full_path_folder]

			## CHECK FOR ILLEGAL Characters in the path name
			if self.is_illegal_path_title(media_folder):
				at_least_one_issue = True

				print ("Found media with a illegal character in the folder name: " + full_path_folder)

				if len(matched_media) == 1:
					self.rename_path_on_disk(matched_media[0], full_path_folder, pushover = pushover, is_test = is_test)
				else:
					print ("    Could not match the media with the illegal character, so could not rename")

			# Look for failed pvr matches.
			if len(matched_media) == 0:
				at_least_one_issue = True

				print ("Could not find a immediate match (using path match) for media in the PVR for (actual folder): " + full_path_folder)

				highest_ratio = 0
				highest_ratio_index = -1
				for idx, media_item in enumerate(media):
					test_ratio = fuzz.ratio(media_item.path, full_path_folder)

					if test_ratio > highest_ratio:
						highest_ratio = test_ratio
						highest_ratio_index = idx

				matched_media = media[highest_ratio_index]
				if highest_ratio > minimum_simularity_ratio and highest_ratio_index != -1:
					print ("     Likely this media: '" + matched_media.title + "', PVR path: " + matched_media.path)

					# Media folder does not have the year (only applicable for movies)
					if media_type == DownloadType.MOVIE and not media_folder.find(str(matched_media.year)) > 0:
						self.rename_path_on_disk(matched_media, full_path_folder, pushover = pushover, is_test = is_test)
					else:
						# Update the PVR path since the actual directory already contains the year
						print ("     Updating the PVR path to: " + full_path_folder)

						matched_media.update_path(full_path_folder)
						matched_media.rescan()				

#						Unsure what this was for....
#						self.rename_path_on_disk(matched_media, matched_media.path, new_path = full_path_folder, pushover = pushover, is_test = is_test)
				else:
					print ("    was not certain enough to make a determination to match the media.  Highest simularity ratio was: " + str(highest_ratio) + ", '" + matched_media.title + "', PVR path: " + matched_media.path)
			
			elif len(matched_media) > 1:
				at_least_one_issue = True

				print ("found more than one match in the PVR for (actual folder): " + full_path_folder)
				pushover.send_pushover_message("Media Manager", "Something wrong matching media from disk to the PVR.  Please review logs.")

		if not at_least_one_issue:
			print ("    everything looks fine...")

		print()