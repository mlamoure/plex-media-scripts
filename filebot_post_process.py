import sys
import requests
from fuzzywuzzy import fuzz
import datetime

from media_manager import PushoverFactory, SeriesFactory, MovieFactory, Movie, Series
from media_manager.core import *


"""
	Expected Filebot execution example:

		--def exec="python3 /path/to/script/filebot_post_process.py \"{n}\" \"{fn}\" \"{folder}\" \"{type}\" \"{s00e00}\" \"{imdbid}\" >> /path/to/log/filebot_post_process.log"
"""


#######################################################
#### BEGIN CONFIG
#######################################################

"""
Whether to use download history of Sonarr / Radarr to match the Movie or Episode to Filebot
"""
USE_DOWNLOAD_HISTORY_FOR_MATCHING = True
MINIMUM_SIMILARITY_RATIO_MOVIE = 80
MINIMUM_SIMILARITY_RATIO_SERIES = 80
NUMBER_HISTORY_ITEMS_TO_CONSIDER = 30 # this is the number of history items to review while matching the movie from filebot

"""
This can be set to False for most people.  Setting this to true will review movies for multiple copies and potentially offer to remove duplicates.
"""
PERFORM_POST_MATCH_OPERATIONS = False

radarr_api_url = "http://10.66.0.1:7878/api"
radarr_api_key = "<your radarr API key>"

sonarr_api_url = "http://10.66.0.1:8989/api"
sonarr_api_key = "<your sonarr API key>"

# Leave these variables empty ("") if not using Pushover.
pushover_app_token = ""
pushover_user_key = ""


#######################################################
#### END CONFIG
#######################################################

assert len(sys.argv) == 7

name = sys.argv[1]
fn = sys.argv[2]
filebot_folder = sys.argv[3].strip()
download_type = sys.argv[4].lower().strip()
series_episode_numbers = sys.argv[5]
tmdbId_tvdbId = int(sys.argv[6])

if filebot_folder[-1] != "/":
	filebot_folder = filebot_folder + "/"

if download_type == "movie":
	download_type = DownloadType.MOVIE
elif download_type == "episode":
	download_type = DownloadType.EPISODE

def load_history(api_url, api_key, item_count = 10):
	history = requests.get(api_url + "/history?page=1&pageSize=" + str(item_count) + "&sortDir=desc&sortKey=date&apikey=" + api_key)

	return history.json()

def review_history(history, download_type, minimum_similarity_ratio, fn, series_episode_numbers = "None"):
	highest_ratio = minimum_similarity_ratio
	highest_ratio_index = None
	reviewed_one = False

	print ('Reviewing Sonarr/Radarr download history to match to download:')
	
	for idx, history_item in enumerate(history["records"]):
		if history_item["eventType"] == "grabbed":
#			print("      Initally looking at '" + history_item["sourceTitle"] + "'")
			if download_type == DownloadType.MOVIE or (download_type == DownloadType.EPISODE and history_item["sourceTitle"].find(series_episode_numbers) > 0):
				reviewed_one = True

				if download_type == DownloadType.MOVIE:
					source_title = history_item["sourceTitle"]
					media_id = history_item["movieId"]
				elif download_type == DownloadType.EPISODE:
					source_title = history_item["sourceTitle"][:history_item["sourceTitle"].find(series_episode_numbers)+6]
					media_id = history_item["seriesId"]
			
				similarity_ratio = fuzz.ratio(source_title, fn)
				print("      Looking at '" + source_title + "', comparing to '" + fn + "', resulting similarity_ratio: " + str(similarity_ratio))

				if similarity_ratio > highest_ratio:
					print ('            found highly similar item (no decision yet): ' + source_title + ", similarity ratio: " + str(similarity_ratio) + ", media (Movie or Series) ID: " + str(media_id))
					highest_ratio = similarity_ratio
					highest_ratio_index = idx

	if not reviewed_one:
		print ('      No Sonarr/Radarr download history matched.')

	return highest_ratio_index, highest_ratio

##############################################################################################################

print ("")
print ('######################################################')
print (str(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")))
print ('Number of arguments:', len(sys.argv), 'arguments.')
print ('  series:', str(name))
print ('  fn:', str(fn))
print ('  folder:', str(filebot_folder))
print ('  download_type:', str(download_type))
print ('  series episode:', str(series_episode_numbers))
print ('  TheMovieDB / TheTVDB ID:', str(tmdbId_tvdbId))
print ("")

#############################
## Create Factories
#############################

pushover = None

if len(pushover_app_token) > 0:
	pushover = PushoverFactory(pushover_app_token, pushover_user_key)

if download_type == DownloadType.MOVIE:
	media_factory = MovieFactory(radarr_api_url, radarr_api_key)
elif download_type == DownloadType.EPISODE:
	media_factory = SeriesFactory(sonarr_api_url, sonarr_api_key)

	if filebot_folder.find("Season") > 0:
		filebot_folder = filebot_folder[:filebot_folder.find("Season")]

#############################
## Initiate variables
#############################
highest_ratio_index = None
similarity_ratio = None
matched = None

#############################
## BEGIN download history match method
#############################

if USE_DOWNLOAD_HISTORY_FOR_MATCHING:
	if download_type == DownloadType.MOVIE:
		history = load_history(radarr_api_url, radarr_api_key, NUMBER_HISTORY_ITEMS_TO_CONSIDER)

		highest_ratio_index, similarity_ratio = review_history(history, download_type, MINIMUM_SIMILARITY_RATIO_MOVIE, fn)

		if highest_ratio_index is not None:
			media_id = int(history["records"][highest_ratio_index]["movieId"])
			matched = Movie(media_id, media_factory)
	
	elif download_type == DownloadType.EPISODE:
		fn = fn[:fn.find(series_episode_numbers)+6]	

		history = load_history(sonarr_api_url, sonarr_api_key, NUMBER_HISTORY_ITEMS_TO_CONSIDER)

		highest_ratio_index, similarity_ratio = review_history(history, download_type, MINIMUM_SIMILARITY_RATIO_SERIES, fn, series_episode_numbers)

		if highest_ratio_index is not None:
			media_id = int(history["records"][highest_ratio_index]["seriesId"])
			matched = Series(media_id, media_factory)

	if highest_ratio_index is None:
		print("Could not match media '" + fn + "' to Radarr/Sonarr download history.  Will proceed to look at the full database of media.")

#############################
## END of download history match method
#############################

#############################
## BEGIN media lookup method
#############################

if matched is None:
	print ()
	print ('Reviewing Sonarr/Radarr full database match to download:')
	media = media_factory.load_from_pvr("All")

	matched = [item for item in media if item == tmdbId_tvdbId]

	if len(matched) != 1:
		print("Could not match media '" + fn + "' to Radarr/Sonarr database.")
		matched = None
	else:
		matched = matched[0]

#############################
## END media lookup method
#############################

if matched is None:
	print ()
	print("Could not match media '" + fn + "' using any methods.  Exiting.")

	if pushover is not None:
		pushover.send_pushover_message("Could not match media", "Could not match '" + fn + "' to any record in Sonarr or Radarr.  Please fix manually.")
	
	exit()

#############################
## Print results for match
#############################

print ("")
print ("Matched: " + matched.title + ", ID: " + str(matched.media_id) + ", TheMovieDB / TheTVDB ID: " + str(matched.public_db_id))
print ("      current Radarr/Sonarr path: " + matched.path)
print ("      filebot (correct) path: " + filebot_folder)

#############################
## Check if the path needs updating in Sonarr / Radarr
#############################

print ()
print ("Reviewing if any path updates need to be made in Sonarr/Radarr:")
if matched.path == filebot_folder:
	print ("    concluded that the path is CORRECT for the media, no change necessary")
else:
	print ("    concluded that the path is incorrect for the media")
	matched.move_media_files(filebot_folder)
	matched.update_path(filebot_folder)

#############################
## Check for any file operations required
#############################

if PERFORM_POST_MATCH_OPERATIONS:
	if download_type == DownloadType.MOVIE:
		media_factory.scan_for_duplicates(matched, pushover, verbose=False)

#############################
## Rescan the media
#############################
matched.rescan()

print ()
print ("DONE!")
print ()
