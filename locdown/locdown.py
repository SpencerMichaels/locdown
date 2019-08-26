import aiohttp, asyncio, contextlib

from fake_useragent import UserAgent

from .argparser import parse_args
from . import action, config, util

async def main_task(args):
  async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(limit=args.max_connections),
        headers={ 'User-Agent': UserAgent().chrome }) as session:
    if args.action == 'download':
      await action.download(session, args, args.max_connections)
    elif args.action == 'scrape':
      await action.scrape(session, args)
    elif args.action == 'stream':
      await action.stream(session, args)

def main(argv):
  # Create the data directory if it does not exist
  if not config.USER_DATA_DIR.is_dir():
    config.mkdir(parents=True, exist_ok=True)

  args = parse_args(argv)

  try:
    loop = asyncio.get_event_loop()
    worker = asyncio.ensure_future(main_task(args))
    loop.run_until_complete(worker)

  except KeyboardInterrupt:
    worker.cancel()
    with contextlib.suppress(asyncio.CancelledError):
      loop.run_until_complete(worker)

  except Exception as e:
    util.die(str(e))

  exit(0)
