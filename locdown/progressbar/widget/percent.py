from . import Padding

class Percent:
  def __init__(self, padding=Padding.NONE):
    self.padding = padding

  def __call__(self, width, state):
    value = (100*state.num_done)//state.num_total
    if self.padding != Padding.NONE:
      return f'{value:{self.padding.value}3d}%'
    return f'{value}%'
