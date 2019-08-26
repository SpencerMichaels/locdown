import asyncio

class TaskBatch:
  def __init__(self, tasks, limit=None, monitor=None, monitor_interval=1):
    self.tasks = list(tasks)
    self.limit = limit or len(self.tasks)
    self.monitor = monitor
    self.monitor_interval = monitor_interval
    self.state = type('state', (), {
      'num_done': 0,
      'num_total': len(self.tasks) })

  async def run(self):
    semaphore = asyncio.Semaphore(self.limit)
    async def run_task(task):
      async with semaphore:
        result = await task
        self.state.num_done += 1
        return result

    async def monitor_task():
      while self.state.num_done < self.state.num_total:
        self.monitor(self.state)
        await asyncio.sleep(self.monitor_interval)
      self.monitor(self.state)

    tasks = [ run_task(task) for task in self.tasks ]
    if self.monitor:
      tasks.append(monitor_task())

    results = await asyncio.gather(*tasks)
    return results[:-1] if self.monitor else results
