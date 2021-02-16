__version__ = 0.147
print(f"Thank you for using pywindowframes. Please report any indecencies to 79141108+afmelin@users.noreply.github.com."
      f"\nPywindowframes version: {__version__}")

from .core import WindowBase
from .core import StaticWindow

from .core import open_or_close_window
from .core import poll_queue
from .core import pop_event
from .core import post_event
from .core import update

from .elements import BaseElement
from .elements import Button
from .elements import DynamicSurface
