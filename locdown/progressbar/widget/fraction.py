from . import Padding

class Fraction:
  def __init__(self, padding=Padding.NONE):
    self.padding = padding

  def __call__(self, width, state):
    if self.padding != Padding.NONE:
      pad_width = len(str(state.num_total))
      return f'{state.num_done:{self.padding.value}{pad_width}d}/{state.num_total}'
    return f'{state.num_done}/{state.num_total}'
