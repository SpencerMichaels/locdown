import asyncio
from itertools import cycle

from util import eprint

SPINNER_CHARS_SHORT = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
SPINNER_CHARS_LONG = '⠁⠁⠉⠙⠚⠒⠂⠂⠒⠲⠴⠤⠄⠄⠤⠠⠠⠤⠦⠖⠒⠐⠐⠒⠓⠋⠉⠈⠈'

class Batch:
  def __init__(self, tasks):
    self.tasks = tasks
    self.num_total = len(tasks)
    self.num_done = 0

  def is_running(self):
    return self.done < self.total

  async def run(self):
    async def do_task(task):
      await task
      self.num_done += 1

    await asyncio.wait([
      self.show_status,
      [ do_task(task) for task in self.tasks ]])

  async def print_status(self, period=1, spinner_chars=SPINNER_CHARS_SHORT):
    sleep_time = len(spinner_chars)/period
    while self.is_running():
      percent_done = (100*self.num_total)//self.num_done
      eprint(f'\r{next(spinner_chars)} {self.num_done}/{self.num_total} ({percent_done}%) complete')
      await asyncio.sleep(sleep_time)
