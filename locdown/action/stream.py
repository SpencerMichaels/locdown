import asyncio

from .. import id, jukebox, util

async def stream(session, args):
  expanded_ids = await id.expand_ids(session, args.recordings)

  async def normalize_id(id_):
    if id_.type_ == id.IDType.ARTIST:
      metadata = await jukebox.scrape_artist(session, id_.value, shallow=True)
      return [ entry.get(jukebox.keys.ID) for entry in metadata.get(jukebox.keys.RECORDINGS) ]
    else:
      return [ id_.value ]

  normalized_ids = util.flatten(await asyncio.gather(*map(normalize_id, expanded_ids)))
  urls = map(lambda id_: jukebox.url.id_to_stream_url(id_, args.bitrate), normalized_ids)

  if (args.print):
    for url in urls:
      print(url)
  else:
    util.open_urls(list(urls))
