PyWindowFrames

///////////////////////////////////////////////////
Quick start guide:
///////////////////////////////////////////////////
Just import module and instantiate a WindowBase instance by supplying it a surface, then call pywindowframes.update()
every frame from your main loop
///////////////////////////////////////////////////


Window classes included:
    WindowBase
        - Features:
            * Can be minimized and then maximized using the minimize/maximize-button top-right
            * Can be closed by clicking the close button top-right
            * Automatically stacks up horizontally at the bottom of the screen if several are minimized. Supports
              over 100 windows (will start to fill rows vertically bottom -> up)
            * Displays a window title (attribute window_title) and automatically resizes to fit the title
            * Snaps to screen edges
            * Drag the window around
            * Overlapping windows retain their relative positions in depth correctly, the focused window is always
              on top

        - Not yet implemented:
            * Resizing by mouse (this is not hard to achieve, I just don't need it right now but it will be implemented)
            * Snapping to other windows (I fear this is tough performance-wise, but will be implemented)

        - Annoyances:
            * Window dragging isn't pixel-perfect. Low priority but I will try to fix it

        - Bugs:
            * Currently bug free through my testing and implementations. Please report any bugs/odd behavior

    StaticWindow
        - Features:
            * Cannot be minimized or maximized
            * Cannot be closed (it can of course be technically closed by setting is_visible == False)
            * Cannot be dragged
            * Has no top border
            * CAN be expanded/collapsed -> think of the windows "Start"-button bringing up the start menu,
              that's what it is.
            * Perfect for GUI for games et c, just fill it with elements

        - Not yet implemented:

        - Annoyances:
            * See WindowBase
        - Bugs:
            * None AFAIK

Elements include:

    BaseElement
        - Features:
            * Can change color when mouse hovers over it
            * Clickable (but does not post any event -> use Button for this)

    Button
        - Features:
            * Has text that is centered in the button
            * Resizes to fit the text
            * Basically a BaseElement that posts a window-event when clicked.
            * The name of the button is what is event-posted: "button_name-was_clicked"

    DynamicSurface
        - Features:
            * Provide it with a function/method that returns a surface and it will display it
            * Perfect for minimaps, dynamic hero portraits et c

Event system
    Is really very simple. Any element can post events to the window instance it belongs to.
    The window instance then posts the event to the module event queue.
    To get events in chronological order; use pwf.pop_event(0) preferably in a loop
    Use pwf.poll_queue to see if there are any events left in the queue.

    Events are stored in the following tuple format: (window_instance, "event_string")

    Example:

    # our event handling function
    def handle_events():

        # loop will keep running until all events have been handled
        while pwf.poll_queue:

            # pop the first event posted (which is list index 0)
            event = pwf.pop_event(0)

            # remember events are tuples: (window_instance, "string")
            if event[1] == "window_close":
                event[0].close()


To be continued...