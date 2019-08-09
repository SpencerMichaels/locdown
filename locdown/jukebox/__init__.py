import asyncio
import urllib

from . import scraper, url

async def scrape(session, id_):
  target = url.id_to_details_url(id_, 'recordings')
  async with session.get(target) as response:
    data = await response.read()
    html = data.decode('utf-8', errors='ignore')
    try:
      return scraper.scrape_recording_details(html)
    except RuntimeError as e:
      text = str(e)
      raise RuntimeError(f'Failed to scrape metadata for recording #{id_}: {str(e)}')

async def find_max_valid_recording_id(session, i0):
  async def is_valid(id_):
    target = url.id_to_details_url(id_, 'recordings')
    try:
      async with session.get(target) as response:
        return response.status == 200
    except urllib.error.HTTPError:
      return False

  i0_was_valid = await is_valid(i0)
  di = 1 if i0_was_valid else -1
  i = i0 + di
  while await is_valid(i) == i0_was_valid:
    i += di
    di *= 2

  max_valid = min(i0, i)
  min_invalid = max(i0, i)

  while max_valid != min_invalid-1:
    i = max_valid + (min_invalid - max_valid)//2
    if await is_valid(i):
      max_valid = i
    else:
      min_invalid = i

  return max_valid

async def download_recording(id_, bitrate=320, filepath=None):
  base_url, playpath = url.id_to_stream_url_parts(id_, bitrate)

  cmd = ['-r', base_url, '-y', playpath]
  if filepath:
    cmd += ['-o', filepath]

  proc = await asyncio.create_subprocess_exec(
      'rtmpdump',
      *cmd,
      stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.PIPE)

  stdout, stderr = await proc.communicate()

  if proc.returncode != 0:
    errstr = stderr.decode('utf-8', errors='ignore')
    raise RuntimeError(f'Rtmpdump failed:\n\n{errstr}')
