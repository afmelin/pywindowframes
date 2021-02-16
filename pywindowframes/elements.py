import pygame as pg
from time import time


class BaseElement:
    def __init__(self, name, window, pos=None, size=None, border=True, grid_pos=None, grid_size=None):
        """
        Using grid size and grid rects is a lot easier than using pos and size directly. Just set a window size
        to a certain grid_size and you will know exactly how much the window will fit, as long as all elements
        are also grid sized

        NOTE: Recommended use is to use grid_pos and grid_size!

        :param name: this is important, it is used as an identifier
        :param window: which window it belongs to
        :param pos: position in pixels. If set to None, grid_pos must be used instead
        :param size: size in pixels. If set to None, grid_size must be used instead
        :param border: bool, border around element
        :param grid_pos: x, y values corresponding to grid rect positions.
        :param grid_size: w, h values corresponding to grid rect sizes (w = 1 == grid_rect_size[0])
        """
        self.name = name  # this is used as identifier when posting events!

        # grid vars
        self.grid_size = grid_size
        self.grid_pos = grid_pos

        self.window = window
        self.window_size = self.window.size
        self.size = self.internal_size(size)
        self.rect = pg.Rect((0, 0), self.size)
        self.pos = self.internal_pos(pos)
        self.pos_string = None

        # surface (transparent per default)
        self.surface = pg.Surface(self.size)
        self.surface.set_colorkey((1, 1, 1))
        self.surface.fill((1, 1, 1))

        # visual
        self.border = border
        self.border_color = (0, 0, 0)
        self.border_mouse_over_color = (255, 0, 0)

        # timings
        self.was_clicked_time = 0

        # click flags
        self.mouse_over = False
        self.clicked = False
        self.dragged = False  # why not? Might be useful

        # other flags
        self.has_changed = True

        # owner window list
        self.window.elements.append(self)

    def internal_pos(self, pos):
        """
        This is the position the element will attempt to assume.
        Coordinates are in window coordinates (excluding top border).

        :param pos: tuple/list of int/float (will be converted to int)
        :return: (int, int)
        """
        x = 0
        y = 0

        if not pos:
            assert isinstance(self.grid_pos, tuple), "No element.pos or element.grid_pos found!" \
                                                     " Use one of them when instancing element"
            x = self.grid_pos[0] * self.window.grid_rect_size[0]
            y = self.grid_pos[1] * self.window.grid_rect_size[1]

        if isinstance(pos, (tuple, list)):
            assert isinstance(pos[0], (int, float)), "element.pos tuple/list must be (int or float, int or float)"
            assert isinstance(pos[1], (int, float)), "element.pos tuple/list must be (int or float, int or float)"
            x = pos[0]
            y = pos[1]
        # print(f"{self.name}, internal pos returned {int(x), int(y)}")
        return int(x), int(y)

    def internal_size(self, size):
        """
        This is the position the element will attempt to assume.
        Coordinates are in window coordinates (excluding top border).

        :param pos: tuple/list of int/float (will be converted to int)
        :return: (int, int)
        """
        x = 0
        y = 0

        if not size:
            assert isinstance(self.grid_size, tuple), "No element.size or element.grid_size found" \
                                                      "Use one of them when instancing element"
            x = self.grid_size[0] * self.window.grid_rect_size[0]
            y = self.grid_size[1] * self.window.grid_rect_size[1]

        if isinstance(size, (tuple, list)):
            assert isinstance(size[0], (int, float)), "Position tuple/list must be (int or float, int or float)"
            assert isinstance(size[1], (int, float)), "Position tuple/list must be (int or float, int or float)"
            x = size[0]
            y = size[1]

        return int(x), int(y)

    def window_has_changed(self, window):
        """
        If the window the element is associated with is changed/reinstanced, this method
        must be called
        """
        self.window = window
        self.window_size = self.window.size
        print("Window instance changed, updating element", self.__class__)

    def set_mouse_over(self):
        """
        Call this for proper behavior, don't change attributes directly
        """
        self.mouse_over = True
        self.has_changed = True

    #@debdec
    def draw(self):
        #  print("Trying to draw element", self.name)
        #  update rect
        self.rect = pg.Rect(self.pos, self.size)

        # mouse over color
        color = self.border_color
        if self.mouse_over:
            color = self.border_mouse_over_color
            # print(f"{self.name} is mouse over and changing color to {self.border_mouse_over_color}")

        #  draw border if True
        if self.border:
            self.surface = pg.Surface(self.size)
            self.surface.set_colorkey((1, 1, 1))
            self.surface.fill((1, 1, 1))
            pg.draw.rect(self.surface, color, (0, 0, self.size[0], self.size[1]), border_radius=10, width=1)

    def post_event(self, event):
        self.window.add_window_event(event)

    #@debdec
    def remake_border(self, radius=0):
        color = self.border_color
        if self.mouse_over:
            color = self.border_mouse_over_color

        pg.draw.rect(self.surface, color, ((0, 0), self.size), width=1, border_radius=radius)

    # @debdec
    def on_click(self):
        self.clicked = True
        self.was_clicked_time = time()
        self.custom_on_click()

    def custom_on_click(self):
        # override if custom behavior is wanted
        pass

    # @debdec
    def reset_flags(self):
        """
        Call this first of all methods when iterating through elements
        """
        if self.clicked:
            self.clicked = False
            self.has_changed = True
        if self.mouse_over:
            self.mouse_over = False
            self.has_changed = True

        self.dragged = False

    #@debdec
    def update(self):
        self.rect = pg.Rect(self.pos, self.size)

        if self.has_changed:
            # print(f"{self.name} has changed = True")
            self.draw()
            self.has_changed = False
        self.custom_update()

    def custom_update(self):
        # override for custom behavior
        pass


class Button(BaseElement):
    def __init__(self, name, window, pos, size, text, border=True, grid_size=None, grid_pos=None):
        super().__init__(name, window, pos, size, border, grid_size, grid_pos)

        # button text
        pg.font.init()
        self.text = text
        self.text_color = (0, 0, 0)
        self.text_font = pg.font.Font(None, 32)
        self.text_surface = self.text_font.render(self.text, False, self.text_color, None)
        self.text_surface_pos = (0, 0)
        self.click_text_color = (255, 0, 0)
        self.text_surface_has_changed = True

        self.adjust_size_to_text()

    # override
    # @debdec
    def custom_on_click(self):
        print(f"{self.name} was clicked")
        event = "-".join([self.name, "was_clicked"])
        self.post_event(event)

    def adjust_size_to_text(self):
        if self.size[0] < self.text_surface.get_size()[0]:
            original_y = self.size[1]
            self.size = self.text_surface.get_size()[0] + 5, original_y

    #@debdec
    def click_text_color_change(self):
        color = self.text_color

        if self.clicked:
            color = self.click_text_color

        self.text_font = pg.font.Font(None, 32)
        self.text_surface = self.text_font.render(self.text, False, color, None)
        self.text_surface_pos = (0, 0)

        self.text_surface_has_changed = True

    def center_text(self):
        self.text_surface_pos = self.size[0] / 2 - self.text_surface.get_size()[0] / 2,\
                                self.size[1] / 2 - self.text_surface.get_size()[1] / 2

    # @debdec
    def custom_update(self):
        self.click_text_color_change()
        if self.text_surface_has_changed:
            self.center_text()
            self.text_surface_has_changed = False

        self.surface.blit(self.text_surface, self.text_surface_pos)


class DynamicSurface(BaseElement):
    """
    Updates it's surface with an external surface on a specified interval
    """
    def __init__(self, name, window, pos=None, size=None, border=True,
                 surface_to_blit_function=None,
                 surface_update_interval=0,
                 grid_pos=None,
                 grid_size=None):
        super().__init__(name, window, pos, size, border, grid_pos, grid_size)

        # see update_surface for instructions
        self.surface_to_blit_position = 0, 0
        self.surface_to_blit_function = surface_to_blit_function
        self.surface_update_interval = surface_update_interval
        self.last_update = 0

    def custom_update(self):
        self.check_interval()

    def check_interval(self):
        if time() > self.last_update + self.surface_update_interval:
            self.update_surface()

    # override
    def draw(self):
        ...

    def resize_to_surface(self):
        ...

    def update_surface(self):
        """
        When instancing this class, provide a reference (surface_to_blit_function)
        to at function complying with the following criteria:
        * No parameters
        * Returns a pygame.Surface

        This surface will be updated each frame or at the interval specified
        """
        surface_to_blit = pg.Surface((0, 0))
        if self.surface_to_blit_function:
            surface_to_blit = self.surface_to_blit_function()
            self.resize_to_surface()

            self.surface.blit(surface_to_blit, (0, 0))
            self.remake_border()
