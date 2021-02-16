"""
How to use:
* Import module
* Call module.init()
* Instantiate all windows you want (and supply a surface to draw to)
* Each frame in your main loop, call module.update()
* Check if there are events generated each frame by using module.poll_event()
* Events from windows will be available through module.pop_event()

TODO:
    * Elements can be clicked through window on top of the element's window [FIXED]
"""
import random
import pygame as pg
from time import time
random.seed()


_windows = []
_window_event_export = []
_highest_layer_number = 0
_minimize_positions = []
_top_border_button_cooldown = 0
_elem_click_cooldown = 0


class WindowBase:
    """
    Empty window. Features:
    * TODO: To allow blitting a window inside another window, huge changes must be made to:
        - The target window's surface must be reblitted after source window blits on it
        - The mouse collision handling must take into account that the source window is inside another window
        - The back-to-front blitting must take into account that the source window is inside another window
        - Right now if the window inside another window has a lower layer it will probably not be clickable
    * Use grid_size instead of size to get a window with a pre-defined grid_size in the big window area
        - this will work with automatic resizing
        - TODO: position the grid rect area so that it is always centered in the window as long as it fits
        - NOTE: Do not use any other method than update_surface() to update the surface, otherwise you will break
        - the window adapting in size to the grid
        - NOTE2: Always check new window sizes with self.limit_window_size(size: tuple)->tuple before changing
    * Automatically resizes to fit grid_size
    * Automatically creates a grid that fits inside
    * TODO: Automatically repositions elements that collide/overlap
    * Resizes automatically to fit window title
    * Snaps to edges
    * Correct unlimited overlap, all windows' depth positions are retained (not for window-in-window)
    * Minimizes and maximizes (see top for optimization to be done)
    * Closes

    Grid terminology:
    * Grid rect = The area defined by self.grid_size (default 16x16 pixels)
    * Grid area = The area defined by (x, y) grid rects (e.g. 10x * self.grid_size[0], 5y * self.grid_size[1])

    To be implemented:
    Snap to other window
    """

    def __init__(self, pos: tuple,
                 size: tuple,
                 target_surface: pg.Surface,
                 window_title: str,
                 visible: bool = True,
                 minimized: bool = False,
                 focused: bool = True,
                 transparent: bool = False,
                 set_grid_size: tuple = None):

        # these 2 need to be mutable
        self.pos = list(pos)
        self.old_pos = self.pos
        self.size = list(size)

        # "backups" when minimizing and maximizing
        self.maximized_size = list[size]
        self.minimized_size = [200, 30]

        # window outline rects
        self.rect = pg.Rect((0, 0), self.size)  # pos, size

        # backup to retrieve when maximizing
        self.rect_backup = self.rect.copy()

        # to where will the window be blitted?
        self.target_surface = target_surface

        # internal surface to draw and blit all window elements
        self.surface = pg.Surface(self.size)
        self.surface.fill((1, 1, 1))
        self.surface.set_colorkey((1, 1, 1))

        # size of buttons in top menu bar
        self.button_size = 20

        # init other window rects
        self.border_rect = pg.Rect((0, 0), (self.rect.w,
                                   self.button_size))
        self.minimize_button_rect = pg.Rect((self.rect.w - (self.button_size * 2), 0),
                                            (self.button_size, self.button_size))
        self.close_button_rect = pg.Rect((self.rect.w - self.button_size, 0),
                                         (self.button_size, self.button_size))

        # text vars
        self.window_title = window_title
        self.original_window_title = self.window_title

        pg.font.init()
        self.window_title_font = pg.font.Font(None, 32)
        self.window_title_surface = self.window_title_font.render(self.window_title, False, (0, 0, 0), None)
        self.window_title_changed = True

        # layer vars (draw on top of other or draw behind other?
        # make sure layer does not match any other window
        self.layer = _highest_layer_number + 1
        report_layer(self.layer)

        # flags
        self.is_focused = focused
        self.is_dragged = False
        self.is_locked = False
        self.can_be_minimized = True
        self.can_be_closed = True
        self.can_be_dragged = True
        self.is_minimized = minimized
        self.is_visible = visible
        self.transparent = transparent

        # mouse flags
        self.m_border_rect = False
        self.m_minimize_button = False
        self.m_close_button = False
        self.m_window_rect = False

        # colors
        self.window_border_color = (0, 0, 0)
        self.window_background_color = (255, 255, 255)
        self.window_background_color_mouse_over = (255, 255, 255)
        self.top_border_background_color_mouse_over = (200, 200, 220)
        self.top_border_background_color = (200, 200, 200)
        self.top_border_button_color = (0, 0, 0)
        self.top_border_button_color_mouse_over = (255, 0, 0)
        self.top_border_top_layer_color = (200, 200, 255)

        # first-run init flag
        self.init = False

        # elements grid
        self.set_grid_size = set_grid_size
        self.grid_rect_size = (16, 16)
        self.grid_size = None
        self.grid_start_position = None
        self.grid_margin = 2

        self.auto_place_elements = True
        # positions on grid
        # access x=3, y=5 like a two-dimensional array
        # i.e. self.grid_positions[3][5]
        # it will return the element occupying that position
        # format [x][y] = None or Obj(Element)
        self.grid_positions = {}

        # internal event queue
        self.window_events = []

        # elements
        self.elements = []

        # add to windows list
        _windows.append(self)

    """
    UPDATES
    """
    def early_update(self):
        if self.is_visible and self.is_dragged:
            self.window_dragging()
            self.snap_to_screen_edges()

        if self.is_visible:
            self.custom_early_update()

    def before_drawing_update(self):
        self.custom_before_drawing_update()

    def drawing_update(self):
        if not self.is_minimized:
            self.resize_to_window_title()
            self.draw_skeleton()
        elif self.is_minimized:
            self.shorten_window_title()
            self.draw_minimized_skeleton()

        self.add_text()

        self.custom_drawing_update()

    def elements_update_early(self):
        if self.is_visible and not self.is_minimized:

            # reset flags first
            if self.elements:
                for elem in self.elements:
                    elem.reset_flags()
        # global elements_mouse_over_buttons(window) is called after this method and before elements_update_late

    def elements_update_late(self):
        # update flags, colors et c
        for e in self.elements:
            e.update()

        # blit
        self.blit_elements()

    def late_update(self):
        self.handle_window_events()
        self.flush_window_events_to_external_event_queue()

        if not self.init:
            self.init_grid()
            self.debug_grid()
            self.init = True

        self.custom_late_update()

    """
    CUSTOM UPDATES
    """
    def custom_early_update(self):
        pass

    def custom_before_drawing_update(self):
        pass

    def custom_drawing_update(self):
        pass

    def custom_elements_update_early(self):
        pass

    def custom_elements_update_late(self):
        pass

    def custom_late_update(self):
        """
        Override this in custom window classes to get custom behavior.
        This is called before window is blitted or selected
        :return:
        """
        pass

    """
    GRID METHODS
    """
    def debug_grid(self):
        #print(self.try_to_occupy_grid_area((0, 0), (100, 100), "TEST_ELEM1"))
        #print(self.try_to_occupy_grid_area((0, 0), (100, 100), "TEST_ELEM2"))
        ...

    # @debdec
    def adapt_window_to_grid_size(self):
        self.grid_size = self.set_grid_size

        # calculate size of window to frame the grid
        attempted_size = int(self.grid_size[0] * self.grid_rect_size[0] + (self.grid_margin * 2)),\
                    int(self.border_rect.h + (self.grid_size[1] * self.grid_rect_size[1]) + (self.grid_margin * 2))

        # adjust size if necessary to not cover more than the available screen resolution (with 10+10 x,y margin)
        adjusted_safe_size = self.limit_window_size(attempted_size)

        # if attempted size was to big, it has been corrected.
        # this means we now have a grid too large for our window size
        # grid needs to be remade, and we simply call init_grid() again which will remake it
        # based on the new size given by limit_window_size()
        if attempted_size != adjusted_safe_size:

            # for this to work, we need to set set_grid_size to None, or else __this__ method will be used again
            self.set_grid_size = None

            # safely set the size to the adjusted safe size
            self.set_permanent_size(adjusted_safe_size)

            # set init to False, which will give some recursion next frame, when grid_init() will be called again
            # and grid_init() will not create a grid based on the size that has just been set
            self.init = False

            # return out of method
            return 0

        # if attempted_size == adjusted_size, no adjust was made.
        # change size and maximized size to match grid
        self.set_permanent_size(adjusted_safe_size)

        # update rect and surface to match new size
        self.update_rect()
        self.update_surface()

        # for this to work, we need to set set_grid_size to None, or else __this__ method will be used again
        self.set_grid_size = None

        self.grid_start_position = self.grid_margin, self.border_rect.h + self.grid_margin
        #print(f"[adapt_window_to_grid_size] grid_size {self.grid_size}, set grid size {self.set_grid_size}, size {self.size}")
        #print(f"surface size {self.surface.get_size()}, self.rect {self.rect}")

    # @debdec
    def grid_size_init(self):
        # set size of window to match grid size
        # also checks so window isn't larger than target surface
        self.adapt_window_to_grid_size()

        # make grid positions dict
        for x in range(0, self.grid_size[0] + 1, 1):
            self.grid_positions[x] = {}
            for y in range(0, self.grid_size[1] + 1, 1):
                self.grid_positions[x][y] = False

        self.set_grid_size = None

    # @debdec
    def limit_window_size(self, size):
        sizex, sizey = size[0], size[1]

        # print("limit input:", size)
        # print("[limit_window_size] target surf size", self.target_surface.get_size())

        if sizex > self.target_surface.get_size()[0]:
            sizex = self.target_surface.get_size()[0] - 10

        if sizey > self.target_surface.get_size()[1]:
            sizey = self.target_surface.get_size()[1] - 10

        #print("[limit_window_size] returning", sizex, sizey)

        return sizex, sizey

    # @debdec
    def init_grid(self):
        # print(f"[init_grid] {self.window_title}")
        # position grid inside the main window area
        if self.set_grid_size:
            return self.grid_size_init()

        # 2 pixel marginal to all sides
        window_area_start = self.grid_margin, self.border_rect.h + self.grid_margin
        window_area_end = self.size[0] - self.grid_margin, self.size[1] - self.border_rect.h - self.grid_margin

        self.grid_start_position = window_area_start

        grid_width = window_area_end[0] - window_area_start[0]
        grid_height = window_area_end[1] - window_area_start[1]

        # how many grid rects can fit?
        x_rects = (grid_width - (grid_width % self.grid_rect_size[0])) / self.grid_rect_size[0]
        y_rects = (grid_height - (grid_height % self.grid_rect_size[1])) / self.grid_rect_size[1]

        self.grid_size = (int(x_rects), int(y_rects))

        # create a dict mapping all grid slots organized x: {y1: True, y2: True, y3: True ...}
        # True is taken, False is available
        for x in range(0, int(x_rects + 1), 1):
            self.grid_positions[x] = {}
            for y in range(0, int(y_rects + 1), 1):
                self.grid_positions[x][y] = False

        # print("[init_grid]", x_rects, y_rects)
        # print("[init_grid]", self.grid_positions)
        # print(f"[init_grid] {self.window_title} created grid: {x_rects} x-rects, {y_rects} y-rects with size {grid_width}, {grid_height}")

    # @debdec
    def set_permanent_size(self, size: tuple):
        assert isinstance(size[0], (int, float)), "size needs to be int or float"
        assert isinstance(size[1], (int, float)), "size needs to be int or float"

        safe_w, safe_h = self.limit_window_size(size)
        old_size = self.size
        new_size = [int(safe_w), int(safe_h)]

        if old_size[0] != new_size[0] or old_size[1] != new_size[1]:
            self.init = False

        self.size = [int(safe_w), int(safe_h)]
        self.maximized_size = [int(safe_w), int(safe_h)]

        self.update_surface()
        self.update_rect()

    def center_in_grid_position(self):
        """
        Center the element in it's grid area
        TODO
        """
        pass

    # TODO implement these great methods - will give auto placement of elements
    def try_to_occupy_grid_area(self, position, element_size, element):
        start_rects = self.calculate_start_grid_rect(position)

        # check if there is room where element is positioned right now
        if self.check_grid_availability(start_rects, element_size):

            self.occupy_area(start_rects, element_size, element)
            return True

        else:

            if self.auto_place_elements:
                return self.try_auto_place_elements(start_rects, element_size)

            else:
                return False

    # TODO implement these great methods - will give auto placement of elements
    def occupy_area(self, start_rects, element_size, element):
        all_rects = self.return_all_grid_rects_needed(start_rects[0], start_rects[1], element_size)

        for x in all_rects:
            for y in all_rects[x]:
                self.grid_positions[x][y] = element

    # TODO implement these great methods - will give auto placement of elements
    def try_auto_place_elements(self, start_rects, element_size):
        """
        Iterate column by column and try to find a suiting spot for the element
        """
        for x in range(start_rects[0],self.grid_size[0]):
            for y in range(start_rects[1], self.grid_size[1]):
                if self.check_grid_availability((x, y), element_size):
                    self.occupy_area((x, y), element_size, ("TEST ELEMENT TRY AUTO PLACE"))
                    return True

        return False

    def return_all_grid_rects_needed(self, start_x_rect, start_y_rect, element_size):
        """
        Takes in starting x, y rects and returns all rects in the occupied grid area as a dict with format:
        occupied_rects = {x1: [y1, y2, y3, ...], ...}
        """
        needed_x, needed_y = self.calculate_amount_grid_rects_needed(element_size)
        end_x = needed_x + start_x_rect
        end_y = needed_y + start_y_rect

        return_dict = {}

        # remember range end point is not counted, however, start rect is counted
        # which is why this range is correct
        for x in range(start_x_rect, end_x):
            return_dict[x] = []
            for y in range(start_y_rect, end_y):
                return_dict[x].append(y)

        return return_dict

    def check_grid_availability(self, start_rects, element_size):
        """
        Takes in start rects (x, y) and grid area needed (element_size)
        Returns True if available, False if unavailable (something else is occupying the position)
        NOTE: Check if grid is large enough for element before calling this method.
        """

        # calculate rects needed (x, y)
        amount_rects_needed = self.calculate_amount_grid_rects_needed(element_size)

        # check all grid rects that will be occupied
        try:
            for x in range(start_rects[0], start_rects[0] + amount_rects_needed[0]):
                for y in range(start_rects[1], start_rects[1] + amount_rects_needed[1]):
                    if self.grid_positions[x][y]:
                        return False

        except KeyError:
            # this case is reached if the object is larger than the available grid
            # print("[check_grid_availability] KeyError. Grid is not large enough for element. Returning False")
            return False

        return True

    def calculate_start_grid_rect(self, position):
        """
        Takes in position in pixels, returns (x, y) grid rect number
        Use this to get the start rect.
        """
        posx = position[0]
        posy = position[1]

        # remove the remainder and divide by grid size to get closest (floor) grid rect
        grid_x = (posx - (posx % self.grid_rect_size[0])) / self.grid_rect_size[0]
        grid_y = (posy - (posy % self.grid_rect_size[1])) / self.grid_rect_size[1]

        return int(grid_x), int(grid_y)

    def available_grid_area(self):
        """
        Returns available grid area
        """
        available_x = 0
        available_y = 0

        for x in self.grid_positions:
            for y in self.grid_positions[x]:
                if not self.grid_positions[x][y]:
                    available_x += self.grid_rect_size[0]
                    available_y += self.grid_rect_size[1]

        return int(available_x), int(available_y)

    def get_grid_area_in_rects(self, area):
        x_rects = area[0] - (area[0] % self.grid_rect_size[0]) / self.grid_rect_size[0]
        y_rects = area[1] - (area[1] % self.grid_rect_size[1]) / self.grid_rect_size[1]

        return int(x_rects), int(y_rects)

    def calculate_grid_area(self, x_rects, y_rects) -> tuple:
        """
        Takes in NUMBER of x, y rects and returns the area in pixels
        """
        return int(x_rects * self.grid_rect_size[0]), int(y_rects * self.grid_rect_size[1])

    def calculate_amount_grid_rects_needed(self, size: tuple) -> tuple:
        """
        Takes in a size, returns the NUMBER of grid rects it occupies (x rects, y rects)
        """
        w = size[0]
        h = size[1]

        gw = (w - (w % self.grid_rect_size[0])) / self.grid_rect_size[0]
        gh = (h - (h % self.grid_rect_size[1])) / self.grid_rect_size[1]

        # increase size by 1 grid if necessary (any size fits this way)
        if self.calculate_grid_area(gw, 0)[0] < size[0]:
            gw += 1
        if self.calculate_grid_area(0, gh)[1] < size[1]:
            gh += 1

        grid_needed = int(gw), int(gh)
        # print(f"[grid_needed] {grid_needed}, {size}")

        return grid_needed

    """
    DRAWING / BLITTING METHODS
    """

    def draw_skeleton(self):
        # Do NOT change size directly. A lot of methods are relying on size == maximized size
        # always use set_permanent_size unless you know what you are doing
        # first reset to maximized values
        if self.size != self.maximized_size:
            self.set_permanent_size(tuple(self.size))

        # print("[draw_skeleton] self.size:", self.size)
        self.surface = pg.Surface(tuple(self.size))
        self.surface.fill((1, 1, 1))
        self.surface.set_colorkey((1, 1, 1))

        # make sure rect is of correct size
        self.rect = pg.Rect((0, 0), tuple(self.size))

        # create rects
        self.border_rect = pg.Rect((0, 0),
                                   (self.rect.w, self.button_size + 10))

        self.minimize_button_rect = pg.Rect((self.rect.w - (self.button_size * 2) - 5, 5),
                                            (self.button_size, self.button_size))

        self.close_button_rect = pg.Rect((self.rect.w - self.button_size - 5, 5),
                                         (self.button_size, self.button_size))

        # colors
        color = self.window_border_color
        top_color = self.window_border_color
        top_fill_color = self.top_border_background_color
        minimize_color = self.top_border_button_color
        close_color = self.top_border_button_color
        window_color = self.window_background_color

        # choose colors
        if self.m_border_rect:
            top_color = (255, 0, 0)
            top_fill_color = self.top_border_background_color_mouse_over

        if self.m_minimize_button:
            minimize_color = self.top_border_button_color_mouse_over

        if self.m_close_button:
            close_color = self.top_border_button_color_mouse_over

        if self.layer == _highest_layer_number:
            top_fill_color = self.top_border_top_layer_color

        if self.m_window_rect:
            window_color = self.window_background_color_mouse_over
            if self.layer != _highest_layer_number:
                top_fill_color = self.top_border_background_color_mouse_over

        if self.transparent:
            self.surface.set_colorkey((1, 1, 1))
            window_color = (1, 1, 1)

        # entire window
        self.surface.fill((window_color), rect=self.rect)
        pg.draw.rect(self.surface, color, self.rect, width=1, border_radius=5,
                     border_top_left_radius=0,
                     border_top_right_radius=0)

        # top border
        self.surface.fill((top_fill_color), rect=self.border_rect)
        pg.draw.rect(self.surface, top_color, self.border_rect, width=1,
                     border_radius=0)

        # button outlines
        pg.draw.rect(self.surface, minimize_color, self.minimize_button_rect, width=1, border_radius=5)
        pg.draw.rect(self.surface, close_color, self.close_button_rect, width=1, border_radius=5)

        # draw minimize "-" and close "X"
        pg.draw.line(self.surface,
                     close_color,
                     (self.close_button_rect.topleft[0] + 2, self.close_button_rect.topleft[1] + 2),
                     (self.close_button_rect.bottomright[0] - 2, self.close_button_rect.bottomright[1] - 2))
        pg.draw.line(self.surface,
                     close_color,
                     (self.close_button_rect.topright[0] - 2, self.close_button_rect.topright[1] + 2),
                     (self.close_button_rect.bottomleft[0] + 2, self.close_button_rect.bottomleft[1] - 2))
        pg.draw.line(self.surface,
                     minimize_color,
                     (self.minimize_button_rect.topleft[0],
                     self.minimize_button_rect.topleft[1] + (self.minimize_button_rect.h / 2)),
                     ((self.minimize_button_rect.topleft[0] + self.minimize_button_rect.w),
                      self.minimize_button_rect.topleft[1] + (self.minimize_button_rect.h / 2))
                     )

    def blit_elements(self):
        self.adjust_element_positions()

        for e in self.elements:
            self.surface.blit(e.surface, e.pos)

    def draw_minimized_skeleton(self):
        # make rect size = top border rect size
        # also make the surface this size
        # text then doesn't need to be changed, because it will not fit if it is too long
        # print("[draw_minimized_skeleton]")
        self.surface = pg.Surface(self.minimized_size)
        self.surface.fill((1, 1, 1))
        self.surface.set_colorkey((1, 1, 1))

        self.rect = pg.Rect((0, 0), self.minimized_size)

        self.border_rect = pg.Rect((0, 0),
                                   (self.rect.w, self.button_size + 10))

        self.minimize_button_rect = pg.Rect((self.rect.w - self.button_size - 5, 5),
                                            (self.button_size, self.button_size))

        color = self.window_border_color
        top_color = self.window_border_color
        top_fill_color = self.top_border_background_color
        minimize_color = self.top_border_button_color
        close_color = self.top_border_button_color

        # remake surface (to adjust its size which is now smaller)
        self.surface = pg.Surface(self.minimized_size)

        if self.m_border_rect:
            top_color = (255, 0, 0)
            top_fill_color = self.top_border_background_color_mouse_over

        if self.m_minimize_button:
            minimize_color = self.top_border_button_color_mouse_over

        if self.m_close_button:
            close_color = self.top_border_button_color_mouse_over

        if self.layer == _highest_layer_number:
            top_fill_color = self.top_border_top_layer_color

        # entire window
        self.surface.fill((255, 255, 255), rect=self.rect)
        pg.draw.rect(self.surface, color, self.rect, width=1, border_radius=5,
                     border_top_left_radius=0,
                     border_top_right_radius=0)

        # top border
        self.surface.fill((top_fill_color), rect=self.border_rect)
        pg.draw.rect(self.surface, top_color, self.border_rect, width=1,
                     border_radius=0)

        # button outlines
        pg.draw.rect(self.surface, minimize_color, self.minimize_button_rect, width=1, border_radius=5)
        # pg.draw.rect(self.surface, close_color, self.close_button_rect, width=1, border_radius=5)

        # draw minimize "-"
        pg.draw.line(self.surface,
                     minimize_color,
                     (self.minimize_button_rect.topleft[0],
                      self.minimize_button_rect.topleft[1] + (self.minimize_button_rect.h / 2)),
                     ((self.minimize_button_rect.topleft[0] + self.minimize_button_rect.w),
                      self.minimize_button_rect.topleft[1] + (self.minimize_button_rect.h / 2))
                     )

    #@debdec
    def update_surface(self):
        #print(f"[update_surface] {self.window_title}")
        old_surf_size = self.surface.get_size()

        # update surface
        self.surface = pg.Surface(self.size)
        self.surface.fill((1, 1, 1))
        self.surface.set_colorkey((1, 1, 1))

        if old_surf_size != self.surface.get_size():
            # need to update grid if surface size has changed
            self.init_grid()

    def update_rect(self):
        self.rect.w = self.size[0]
        self.rect.h = self.size[1]

    """
    WINDOW POSITIONING
    """

    def snap_to_screen_edges(self):
        """
        Self explanatory
        """
        # how far from the edge will the window snap to the edge?
        snap_distance = 10

        if self.pos[0] < snap_distance:
            self.pos[0] = 0
        if self.pos[0] > self.target_surface.get_size()[0] - self.rect.w - snap_distance:
            self.pos[0] = self.target_surface.get_size()[0] - self.rect.w

        if self.pos[1] < snap_distance:
            self.pos[1] = 0
        if self.pos[1] > self.target_surface.get_size()[1] - self.rect.h - snap_distance:
            self.pos[1] = self.target_surface.get_size()[1] - self.rect.h

    def window_dragging(self):
        if self.can_be_dragged:
            mx, my = pg.mouse.get_rel()
            # print(f"window dragging, mx, my: {mx, my}")

            self.pos[0] += mx
            self.pos[1] += my

    """
    ELEMENT POSITIONING
    """

    def adjust_element_positions(self):
        for e in self.elements:
            # left adjust
            if e.pos[0] < self.grid_margin:
                e.pos = self.grid_margin, e.pos[1]
                e.has_changed = True
                # print(e.name, "moved to x==5")

            # right adjust
            elif e.pos[0] + e.size[0] > self.size[0] - e.size[0] - self.grid_margin:
                e.pos = self.size[0] - e.size[0] - self.grid_margin, e.pos[1]

            # top adjust
            if e.pos[1] < self.border_rect.h + self.grid_margin:
                e.pos = e.pos[0], self.border_rect.h + self.grid_margin

            elif e.pos[1] + e.size[1] > self.size[1] - e.size[1] - self.grid_margin:
                e.pos = e.pos[0], self.size[1] - e.size[1] - self.grid_margin


    """
    TEXT METHODS
    """

    def add_text(self):
        self.surface.blit(self.window_title_surface, (5, 5))

    def expand_window_title(self):
        self.window_title = self.original_window_title
        self.update_text()

    def shorten_window_title(self):
        shortened_title = self.window_title[:14]
        self.window_title = shortened_title
        self.update_text()

    def change_window_text(self, text):
        self.window_title = text
        self.window_title_changed = True

    def update_text(self):
        self.window_title_font = pg.font.Font(None, 32)
        self.window_title_surface = self.window_title_font.render(self.window_title, False, (0, 0, 0), None)
        self.window_title_changed = True

    def resize_to_window_title(self):
        if self.window_title_changed:
            current_window_width = self.size[0]
            required_window_width = self.window_title_surface.get_size()[0] + (3 * self.button_size) + 10

            if required_window_width != current_window_width:
                if required_window_width > current_window_width:
                    self.size[0] = required_window_width

                # also update maximized size
                if not self.is_minimized:
                    self.maximized_size = self.size

            # update rect
            self.update_rect()

            # we must update surface aswell
            self.update_surface()

            self.window_title_changed = False

    def reset_mouse_over_flags(self):
        self.m_border_rect = False
        self.m_minimize_button = False
        self.m_close_button = False
        self.m_window_rect = False

        self.is_dragged = False

    """
    LAYERING / WINDOW FOCUS
    """

    def increase_layer(self):
        self.layer += 1

    def focus_window(self):
        """
        Focus window = make it drawn last = put it in front
        All other windows retain their original layer
        Elegant :)
        """
        global _highest_layer_number
        if self.layer == _highest_layer_number:
            pass
        else:
            self.layer = _highest_layer_number + 1
            report_layer(self.layer)

    """
    OPENING / CLOSING WINDOW
    """

    def close(self):
        if self.can_be_closed:
            self.is_visible = False

    def open(self):
        self.is_visible = True

    """
    EVENTS
    """

    def add_window_event(self, event):
        self.window_events.append(event)

    def remove_window_event(self, event):
        if event in self.window_events:
            self.window_events.remove(event)

    def flush_window_events_to_external_event_queue(self):
        for event in self.window_events:
            post_event((self, event))
            self.window_events.remove(event)

    def handle_window_events(self):
        # print("Events:", [s for s in self.window_events], "in window", self.window_title)
        ...


class StaticWindow(WindowBase):
    """
    Features:
        * Cannot be minimized, closed or dragged (perfect for parts of a UI)
        * Can however be collapsed into a smaller form (like a button - e.g. the windows start menu)
        * Remains open while StaticWindow.instance.is_constantly_expanded == True
        * Or just set it to is_constantly_expanded to keep it constantly expanded
    """
    def __init__(self, pos, size, target_surface: pg.Surface, window_title: str, set_grid_size=None,
                 background_color=None,
                 background_surface=None,
                 collapsed_size=(30, 30),
                 is_constantly_expanded=False):
        super().__init__(pos, size, target_surface, window_title, set_grid_size=set_grid_size)

        self.collapsed_size = collapsed_size
        self.is_constantly_expanded = is_constantly_expanded
        self.constantly_expanded_button_color = (0, 0, 50)
        self.expand_button_rect = pg.Rect((0, 0), (30, 30))

        # override
        self.can_be_dragged = False
        self.can_be_closed = False
        self.can_be_minimized = False

        if background_color:
            self.window_background_color = background_color
        self.background_surface = background_surface

        # unique flags
        self.is_collapsed = False

    def change_expansion_state(self):
        if self.is_constantly_expanded:
            self.is_constantly_expanded = False
        elif not self.is_constantly_expanded:
            self.is_constantly_expanded = True

    # override
    def draw_skeleton(self):
        if self.background_surface:
            self.surface.blit(self.background_surface, (0, 0))

        if self.window_background_color:
            self.surface.fill(self.window_background_color)

        if not self.is_constantly_expanded:
            if self.m_window_rect:
                self.size = self.maximized_size
                self.update_rect()
                self.update_surface()

                pg.draw.rect(self.surface, self.window_border_color, self.rect, width=1)

            if not self.m_window_rect:
                self.size = self.collapsed_size
                self.update_rect()
                self.update_surface()

                pg.draw.rect(self.surface, self.window_border_color, self.rect, width=1)

        if self.is_constantly_expanded:
            #print("is constantly expanded")
            self.size = self.maximized_size
            self.update_rect()
            self.update_surface()
            self.surface.fill(self.window_background_color)

            pg.draw.rect(self.surface, self.window_border_color, self.rect, width=1)

# override
    def close(self):
        pass

    # override
    def add_text(self):
        pass

    # override
    def adjust_element_positions(self):
        pass


def update():
    """
    This method is the one to use to add methods that need updating inside window class
    """
    window_update()
    window_selection()
    back_to_front_blitting()


def window_update():
    for w in _windows:
        index = 0
        # print(index, w.window_title, w.size, w.surface.get_size())
        index += 1

        if w.is_visible:
            w.early_update()
            #print(index, w.window_title, w.size, w.surface.get_size())
            index += 1

        if w.is_visible:
            w.drawing_update()
            #print(index, w.window_title, w.size, w.surface.get_size())
            index += 1

        if w.is_visible and not w.is_minimized:
            w.elements_update_early()
            elements_mouse_over_clicks(w)
            w.elements_update_late()

        if w.is_visible:
            w.late_update()


def back_to_front_blitting():
    """
    Blit all window surfaces back to front
    """
    global _windows
    # make a list of all windows ordered by layer
    windows_copy = _windows.copy()
    ordered_list_of_windows = []

    # determine order of windows
    while windows_copy:
        for x in windows_copy:
            if x.layer == min([s.layer for s in windows_copy]):
                # this gives a front-to-back ordered list
                ordered_list_of_windows.append(x)
                windows_copy.remove(x)

    while ordered_list_of_windows:
        # pop the first item in the list to get back-to-front order

        # only blit visible windows
        window_to_blit = ordered_list_of_windows.pop(0)
        if window_to_blit.is_visible:
            window_to_blit.target_surface.blit(window_to_blit.surface, window_to_blit.pos)


def window_selection():
    # TODO most likely doesn't take into account if window is visible or not
    # TODO implement

    top_layer_window = test_multiple_window_collision()
    # print(f"Window layers: {[s.layer for s in _windows]}")

    # this alternative happens when mouse is over 1 or more windows
    # if they are overlapping each other,
    # top_layer_window is the window amongst them with the highest layer number
    if top_layer_window:
        for w in _windows:
            if w is not top_layer_window:
                w.reset_mouse_over_flags()

        buttons_mouse_over_internal(top_layer_window)

    # this alternative happens if the mouse is not over any window that is in top level
    if not top_layer_window:
        for w in _windows:
            w.reset_mouse_over_flags()
            buttons_mouse_over_internal(w)


def test_multiple_window_collision():
    """
    Works
    """
    # if multiple windows are stacked, only the one in the front will be mouse-overed/clicked
    # determine which window has the highest layer

    collided_windows = []
    top_layer_window = None
    for w in _windows:
        if adjusted_mouse_rect_collision(w, w.rect):
            collided_windows.append(w)

    for w in collided_windows:
        if w.is_visible:
            if w.layer == max(w.layer for w in collided_windows):
                top_layer_window = w
                return top_layer_window

    return None


def adjusted_mouse_rect_collision(window, rect):
    mx, my = pg.mouse.get_pos()

    # convert to screen coordinates
    scrx = mx - window.pos[0]
    scry = my - window.pos[1]

    # print("adjust mouse rect collision returning mouse click in window at pos", scrx, scry)

    if rect.collidepoint(scrx, scry):
        return True

    return False


def buttons_mouse_over_internal(window):
    """
    Checks if mouse is over any window part and if the part is clicked
    If a mouse click registers, posts an event that pywindowframes caught the click
    """

    # reset flags
    window.reset_mouse_over_flags()

    # no click detection if window is not visible
    if not window.is_visible:
        return 0

    if adjusted_mouse_rect_collision(window, window.border_rect):
        window.m_border_rect = True

        # minimize button clicked
        if window.can_be_minimized and adjusted_mouse_rect_collision(window, window.minimize_button_rect):
            window.m_minimize_button = True

            if mouse0_cd():

                if window.is_minimized:
                    maximize(window)

                elif not window.is_minimized:
                    minimize(window)

                # post event that pywindowframes caught the mouse click
                post_event((window, "pywindowframes_clicked"))

        # close button clicked
        elif adjusted_mouse_rect_collision(window, window.close_button_rect):

            window.m_close_button = True

            if mouse0_cd():

                window.close()

                # post event that pywindowframes caught the mouse click
                post_event((window, "pywindowframes_clicked"))

        # top border is clicked but no button in top border
        else:
            if pg.mouse.get_pressed(num_buttons=3)[0]:

                window.is_dragged = True
                window.focus_window()

                # post event that pywindowframes caught the mouse click
                post_event((window, "pywindowframes_clicked"))

        # reset mouse rel (because it returns mouse rel since it was last _called_
        if not window.is_dragged:
            pg.mouse.get_rel()

    # window rect collision
    if adjusted_mouse_rect_collision(window, window.rect):

        window.m_window_rect = True

        if not window.is_minimized:
            if mouse0_cd():
                # print("Window clicked")
                window.focus_window()

                # post event that pywindowframes caught the mouse click
                post_event((window, "pywindowframes_clicked"))

    else:
        window.m_window_rect = False


# @debdec
def elements_mouse_over_clicks(window):
    # first find the top level window if several is collided
    top_level_window = test_multiple_window_collision()

    for e in window.elements:
        # print(e.name, "found with rect", e.rect)
        # print("mouse was clicked at pos", pg.mouse.get_pos())
        if adjusted_mouse_rect_collision(window, e.rect):

            # only allow clicking on the top level window if several windows are stacked
            if top_level_window:
                if e.window == top_level_window:
                    e.set_mouse_over()
                    #print(f"Mouse over {e.name} in top level")

                    if mouse0_cd(elem=True):
                        # print("mouse clicked (top level)")
                        e.on_click()

                        # post event that pywindowframes caught the mouse click
                        post_event((window, "pywindowframes_clicked"))

            # if windows are not stacked, allow mouse over and clicking as usual
            else:
                e.set_mouse_over()
                print(f"Mouse over {e.name} in no top level (no overlapping windows at mouse pos)")

                if mouse0_cd(elem=True):
                    # print("mouse clicked (no window stacking)")
                    e.on_click()

                    # post event that pywindowframes caught the mouse click
                    post_event((window, "pywindowframes_clicked"))


"""
LAYER CONTROL
"""


def report_layer(layer: int):
    """
    makes sure new windows always get assigned the highest layer
    :param layer:
    :return:
    """
    global _highest_layer_number

    if layer > _highest_layer_number:
        _highest_layer_number = layer


"""
MAXIMIZE / MINIMIZE 
"""


def maximize(window):
    release_minimize_position(window.pos)
    window.pos = window.old_pos
    window.expand_window_title()
    window.is_minimized = False


def minimize(window):
    """
    Minimizes window
    """
    global _minimize_positions
    if window.can_be_minimized:
        window.old_pos = window.pos

        # get a valid position
        window.pos = get_minimize_position(window)

        # report this position to the list of positions
        _minimize_positions.append(window.pos)

        window.is_minimized = True


def get_minimize_position(window) -> list[int, int]:
    """
    Possible minimize positions are stored as a list of tuples.
    First value is x-position and second value is if it is already used or not.
    This function will iterate from beginning to end and return the first
    available x-position for a window to be minimized to.
    """
    global _minimize_positions

    # first determine first possible position
    posx = 0
    posy = window.target_surface.get_size()[1] - window.minimized_size[1]

    # if position is unavailable, modify it
    while [posx, posy] in _minimize_positions:
        # print("posx in _minimize_positions")
        posx += window.minimized_size[0]
        if posx + window.minimized_size[0] > window.target_surface.get_size()[0]:
            # print("posx", posx, "larger than surface size", window.target_surface.get_size()[0])
            posx = 0
            posy -= window.minimized_size[1]
    # print("[get_minimize_position] returning:", posx, posy)
    return [posx, posy]


def release_minimize_position(position: tuple[int, int] or list[int, int]):
    global _minimize_positions

    index = 0
    for listpos in _minimize_positions:
        if listpos == position:
            _minimize_positions.remove(listpos)


def open_or_close_window(window):
    for w in _windows:
        if w == window:

            if w.is_visible and not w.is_minimized:
                w.close()

            elif w.is_visible and w.is_minimized:
                maximize(window)

            elif not w.is_visible:
                if w.is_minimized:
                    maximize(window)
                w.open()
"""
MODULE INIT
"""


def init():
    pass


"""
EVENT HANDLING
"""


def post_event(event: tuple[object, str]):
    """
    Post event to the event queue
    format: (window_obj, event_string)
    """
    if event not in _window_event_export:
        _window_event_export.append(event)


def pop_event() -> tuple[object, str] or None:
    """
    Returns event if one is in queue
    If queue is empty, returns None
    """
    if _window_event_export:
        event = _window_event_export.pop(0)
        # print("popping event:", event)
        return event

    else:
        return None


def poll_queue() -> bool:
    if _window_event_export:
        return True
    else:
        return False


# click cool down
def mouse0_cd(elem=False):
    """
    Call this to check if mouse button 0 (left) has been clicked
    Only returns True if click is off cool down (to prevent click*frame rate amount of clicks in a single click)
    :return bool:
    """
    global _top_border_button_cooldown
    global _elem_click_cooldown

    t = time()
    if not elem:
        if t > _top_border_button_cooldown and pg.mouse.get_pressed(num_buttons=3)[0]:
            _top_border_button_cooldown = t + 0.5
            return True

    if elem:
        if t > _elem_click_cooldown and pg.mouse.get_pressed(num_buttons=3)[0]:
            _elem_click_cooldown = t + 0.5
            return True

    return False
