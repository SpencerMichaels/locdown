from collections import namedtuple
import re

STREAM_URL_BASE = 'rtmp://stream.media.loc.gov/vod/'
STREAM_URL_PLAYPATH = 'mp3:jukebox/%d_%d'
DETAILS_URL_FMTSTR = 'https://www.loc.gov/jukebox/%s/detail/id/%d'
URL_REGEX = re.compile(r'^https?:\/\/(www\.)?loc\.gov\/jukebox\/([a-z]+)\/detail\/id\/(\d+)\/?$')

ID = namedtuple('ID', 'id_ type_')

def url_to_id(url):
  match = URL_REGEX.match(url)

  if not match:
      raise ValueError('Invalid URL: %s' % (url))

  id_ = int(match.group(3))
  type_ = match.group(2)

  return ID(id_, type_)

def id_to_stream_url(recording_id, bitrate=320):
  return STREAM_URL_BASE + STREAM_URL_PLAYPATH % (recording_id, bitrate)

def id_to_stream_url_parts(recording_id, bitrate=320):
  return STREAM_URL_BASE, STREAM_URL_PLAYPATH % (recording_id, bitrate)

def id_to_details_url(id_, domain):
  return DETAILS_URL_FMTSTR % (domain, id_)
