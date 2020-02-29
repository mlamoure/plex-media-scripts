import math
from enum import Enum

class DownloadType(Enum):
	MOVIE = 0
	EPISODE = 1

class RIPType(Enum):
	WEBRIP = 0
	WEBDL = 1
	REMUX = 2

def convert_size(size_bytes):
   if size_bytes == 0:
	   return "0B"
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   s = round(size_bytes / p, 2)
   return "%s %s" % (s, size_name[i])

class RESOLUTION(Enum):
	SD = 0
	HD720 = 1
	FULLHD = 2
	UHD = 3