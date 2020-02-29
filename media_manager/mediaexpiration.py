from fuzzywuzzy import fuzz
import requests
import datetime
from datetime import timedelta
import os
import json

from .core import *

FUZZY_STRING_RATIO = 97
WARN_EXPIRE_DAYES = 14

class MediaExpirationRecord(object):
	def __init__(self, media_title, media_id, folder, date, never_flag):
		self.date = date

		if not folder.endswith("/"):
			folder = folder + "/"

		folder = folder.strip()

		if not os.path.isdir(folder):
			print("Expire record warning: not a valid directory: " + folder)

		self.folder = folder
		self.never = bool(never_flag)
		self.media_id = media_id
		self.media_title = media_title

	def json(self):
		postjson = {
				"movieID": self.media_title,
				"media_id": self.media_id,
				"title" : self.media_title,
				"folder": self.folder,
				"never": bool(self.never),
				"expiration": self.date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
			}
		
		return (postjson)

	def is_expired(self):
		if self.never:
			return False

		return datetime.datetime.now() > self.date

	def is_valid(self):
		if self.never:
			return True

		try:
			test = self.date - datetime.datetime.now()
		except:
			return False

		return True
	
	def will_expire_in_days(self):
		return (self.date - datetime.datetime.now()).days

	def check_if_will_expire_in(self, days):
		if self.never:
			return False

		return (datetime.datetime.now() + datetime.timedelta(days=days)) > self.date

class MediaExpirationFactory(object):
	def __init__(self, service_url):
		self._service_url = service_url
		self.load_from_web_service()

	def match_movies(self, movies):
		expiration_count = 0
		missing_count = 0

		for movie in movies:
			movie_found = False
			for expiration_record in self._expire_records:
				if fuzz.ratio(expiration_record.folder, movie.path) > FUZZY_STRING_RATIO:
					movie.expiration_record = expiration_record
					expiration_record.movie = movie
					movie_found = True
					expiration_count = expiration_count + 1
					break

			if not movie_found:
				missing_count = missing_count + 1
				print("Warning: Did not find a expiration record for movie '" + movie.title + "'")
#			elif movie_found:
#				print("Loaded expiration record for movie '" + movie.title + "' date: '" + str(movie.expiration_record.date) + "'")

		print ("Loaded " + str(expiration_count) + " expiration records.  Missing " + str(missing_count) + " expiration records.")
		print ()

	def validate_movie_expiration_records(self, movies, pushover = None):
		default_date = datetime.datetime.now() + timedelta(days=365)

		missing_content = [item for item in self._expire_records if not os.path.isdir(item.folder)]
		invalid_expire_records = [item for item in self._expire_records if not item.is_valid()]

		if len(missing_content) > 0 or len(invalid_expire_records) > 0:
			print ("######## Expiration Record Validation ########")

		# remove movies that are no longer present
		for bad_record in missing_content:
			print("expire record for " + bad_record.folder + " does not exist, removing")
			self.remove_expire_record(bad_record.media_id)

		# remove movies that are no longer present
		for bad_record in invalid_expire_records:
			print("expire record for " + bad_record.folder + " invalid expiration date, removing")
			self.remove_expire_record(bad_record.media_id)

		# add movies that are missing
		for movie in movies:
			if not hasattr(movie, "expiration_record") or movie.expiration_record is None:
				if len(movie.media_files) > 1:
					new_expiration_record = MediaExpirationRecord(movie.title, movie.movie_id, movie.path, default_date + timedelta(days=365), True)
				elif movie.best_rip_type() == RIPType.REMUX:
					new_expiration_record = MediaExpirationRecord(movie.title, movie.movie_id, movie.path, default_date + timedelta(days=365), False)
				else:
					new_expiration_record = MediaExpirationRecord(movie.title, movie.movie_id, movie.path, default_date, False)
				

				new_expiration_record_log = "adding a expiration record for missing movie: '" + movie.title + "'\n"
				new_expiration_record_log = new_expiration_record_log + "     Expiration Date: " + new_expiration_record.date.strftime("%Y-%m-%d") + ", Never Flag: " + str(new_expiration_record.never) + "\n"

				if pushover is not None:
					pushover.send_pushover_message("Media Manager Script", new_expiration_record_log)
	
				print (new_expiration_record_log)

				self._expire_records.append(new_expiration_record)
				self.add_expire_record(new_expiration_record.json())
				movie.expiration_record = new_expiration_record

	def remove_expire_record(self, record_id):
		r = requests.delete(self._service_url + "/movies/" + str(record_id))
		return True

	def add_expire_record(self, json_data):
		headers = {'Content-Type': 'application/json'}
		r = requests.post(self._service_url + "/movies/", data=json.dumps(json_data), headers=headers)

		return True

	def load_from_web_service(self):
		self._expire_records = []

		r = requests.get(self._service_url + "/movies/all")

		for media_expiration_record in r.json()["movies"]:
			never = False

			if media_expiration_record["expiration"].lower() == "never" or ("never" in media_expiration_record and media_expiration_record["never"] == True):
				date = datetime.datetime.now() + timedelta(days=365)
				never = True
			else:
				try:
					date = datetime.datetime.strptime(media_expiration_record["expiration"], '%Y-%m-%dT%H:%M:%S.%f')
				except:
					try:
						date = datetime.datetime.strptime(media_expiration_record["expiration"], '%Y-%m-%dT%H:%M:%S.%fZ')
					except:
						try:
							date = datetime.datetime.strptime(media_expiration_record["expiration"], '%Y-%m-%d %H:%M:%S.%f')
						except:
							print("movie had a unparsable expiration date: " + movie["movieID"])

			folder = media_expiration_record["folder"].strip()
			media_id = media_expiration_record["movieID"]

			media_title = ""
			if "title" in media_expiration_record:
				media_title = media_expiration_record["title"]

			new_record = MediaExpirationRecord(media_title, media_id, folder, date, never)

			self._expire_records.append(new_record)

	def warn_near_expiration(self, movies, pushover, skip_early_earning = False):
		will_expire_soon_records = [item for item in self._expire_records if item.check_if_will_expire_in(WARN_EXPIRE_DAYES)]
		logtext = ""

		if not skip_early_earning:
			print("##### Early warning for UHD Movies #####")

			for movie in movies:
				if movie.expiration_record is not None and not movie.expiration_record.never and movie.expiration_record.will_expire_in_days() < 365:
					if (movie.best_rip_type() == RIPType.REMUX and movie.resolution == RESOLUTION.UHD) or len(movie.media_files) > 1:
						print("consider changing the expiration for movie '" + movie.title + "', as it is a UHD movie / movie with multiple copies that expires in " + str(movie.expiration_record.will_expire_in_days()) + " days.")

		if len(will_expire_soon_records) > 0:
			logtext = logtext + "##### Near-term expiration #####\n"
			logtext = logtext + "expiration for the following " + str(len(will_expire_soon_records)) + " movies will happen in the next " + str(WARN_EXPIRE_DAYES) + " days: \n"

			for record in will_expire_soon_records:
				logtext = logtext + "       " + record.movie.title + " (" + record.date.strftime("%Y-%m-%d") + ", " + str(record.will_expire_in_days()) + " days)\n"

		if pushover is not None:
			pushover.send_pushover_message("Media Manager Script", logtext)

		print(logtext)

	def delete_expired_content(self, is_test = False, pushover = None):
		expired_records = [item for item in self._expire_records if item.is_expired()]
		not_expired_records = [item for item in self._expire_records if item.is_expired()]

		logtext = "######## Past due media expirations ########\n"
		logtext = logtext + "expiration for the following " + str(len(expired_records)) + " movies has passed: \n"

		for record in expired_records:
			logtext = logtext + "     " + record.movie.title + " (" + record.date.strftime("%Y-%m-%d") + ")\n"

			if not is_test:
				shutil.rmtree(record.folder)
				self.remove_expire_record(record.media_id)

			### TODO: Remove the records from the expiration DB and Radarr.

		if len(expired_records) == 0:
			logtext = "######## Past due media expirations ########\n"
			logtext = logtext + "    No movies are expired\n"
		else:
			logtext = logtext + "\nACTION TAKEN: Deleted!"
			pushover.send_pushover_message("Media Manager Script", logtext)		

		print(logtext)
