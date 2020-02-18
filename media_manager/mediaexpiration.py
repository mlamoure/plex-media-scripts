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
	def __init__(self, movie_id, folder, date, never_flag):
		self.date = date

		if not folder.endswith("/"):
			folder = folder + "/"

		folder = folder.strip()

		if not os.path.isdir(folder):
			print("Expire record warning: not a valid directory: " + folder)

		self.folder = folder
		self.never = bool(never_flag)
		self.movie_id = movie_id

	def json(self):
		postjson = {
				"movieID": self.movie_id,
				"folder": self.folder,
				"never": bool(self.never),
				"expiration": str(self.date)
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

	def validate_movie_expiration_records(self, movies):
		print ("######## Expiration Record Validation ########")
		default_date = datetime.datetime.now() + timedelta(days=365)

		missing_content = [item for item in self._expire_records if not os.path.isdir(item.folder)]
		invalid_expire_records = [item for item in self._expire_records if not item.is_valid()]

		# remove movies that are no longer present
		for bad_record in missing_content:
			print("expire record for " + bad_record.folder + " does not exist, removing")
			self.removeExpireRecord(bad_record)

		# remove movies that are no longer present
		for bad_record in invalid_expire_records:
			print("expire record for " + bad_record.folder + " invalid expiration date, removing")
#			self.removeExpireRecord(bad_record)

		# add movies that are missing
		for movie in movies:
			if movie.expiration_record is None:
				print("adding a expiration record for missing movie: '" + movie.title + "'")

				if movie.best_rip_type() == RIPType.REMUX or movie.resolution == RESOLUTION.UHD or len(movie.media_files) > 1:
					new_expiration_record = MediaExpirationRecord(movie.movie_id, movie.path, default_date + timedelta(days=730), True)
				else:
					new_expiration_record = MediaExpirationRecord(movie.movie_id, movie.path, default_date, False)
				
				self._expire_records.append(new_expiration_record)
				self.add_expire_record(new_expiration_record.json())

			elif movie.expiration_record is not None and not movie.expiration_record.never and movie.expiration_record.will_expire_in_days() < 365:
				# Update the expiration for any movie that fits criteria
				if movie.best_rip_type() == RIPType.REMUX or movie.resolution == RESOLUTION.UHD or len(movie.media_files) > 1:
					print ("consider changing the expiration for movie '" + movie.title + "', as it is a UHD movie that expires in " + str(movie.expiration_record.will_expire_in_days()) + " days.")


	def add_expire_record(self, json_data):
		headers = {'Content-Type': 'application/json'}
		r = requests.post(self._service_url + "/movies/", data=json.dumps(json_data), headers=headers)

		return True

	def load_from_web_service(self):
		self._expire_records = []

		r = requests.get(self._service_url + "/movies/all")

		for movie_expiration_record in r.json()["movies"]:
			never = False

			if movie_expiration_record["expiration"].lower() == "never" or ("never" in movie_expiration_record and movie_expiration_record["never"] == True):
				date = datetime.datetime.now() + timedelta(days=365)
				never = True
			else:
				try:
					date = datetime.datetime.strptime(movie_expiration_record["expiration"], '%Y-%m-%dT%H:%M:%S.%f')
				except:
					try:
						date = datetime.datetime.strptime(movie_expiration_record["expiration"], '%Y-%m-%dT%H:%M:%S.%fZ')
					except:
						try:
							date = datetime.datetime.strptime(movie_expiration_record["expiration"], '%Y-%m-%d %H:%M:%S.%f')
						except:
							print("movie had a unparsable expiration date: " + movie["movieID"])

			folder = movie_expiration_record["folder"].strip()
			movie_id = movie_expiration_record["movieID"]

			new_record = MediaExpirationRecord(movie_id, folder, date, never)

			self._expire_records.append(new_record)

	def warn_near_expiration(self, pushover):
		will_expire_soon_records = [item for item in self._expire_records if item.check_if_will_expire_in(WARN_EXPIRE_DAYES)]

		logtext = "\n######## Upcoming media expirations ########\n"
		logtext = logtext + "expiration for the following " + str(len(will_expire_soon_records)) + " movies will happen in the next " + str(WARN_EXPIRE_DAYES) + " days: \n"

		for record in will_expire_soon_records:
			logtext = logtext + "       " + record.movie.title + " (" + record.date.strftime("%Y-%m-%d") + ", " + str(record.will_expire_in_days()) + " days)\n"

		if len(will_expire_soon_records) == 0:
			logtext = logtext + "     no movies set to expire"

		print(logtext)
		pushover.SendPushoverMessage("Media Manager Script", logtext)

	def delete_expired_content(self, is_test, pushover):
		expired_records = [item for item in self._expire_records if item.is_expired()]
		not_expired_records = [item for item in self._expire_records if item.is_expired()]

		logtext = "######## Past due media expirations ########\n"
		logtext = logtext + "expiration for the following " + str(len(expired_records)) + " movies has passed: \n"

		for record in expired_records:
			logtext = logtext + "     " + record.movie.title + " (" + record.date.strftime("%Y-%m-%d") + ")\n"

			if not is_test:
				shutil.rmtree(record.folder)
				self.removeExpireRecord(record)

			### TODO: Remove the records from the expiration DB and Radarr.

		if len(expired_records) == 0:
			logtext = "######## Past due media expirations ########\n"
			logtext = logtext + "    No movies are expired\n"
		else:
			logtext = logtext + "\nACTION TAKEN: Deleted!"
		

		print(logtext)
		pushover.SendPushoverMessage("Media Manager Script", logtext)