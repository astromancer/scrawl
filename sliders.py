import logging
# import operator


import numpy as np
from cycler import cycler
from matplotlib.lines import Line2D

# from matplotlib.widgets import AxesWidget, Slider
# from matplotlib.patches import Circle
#
# from matplotlib.transforms import Affine2D
# from matplotlib.transforms import blended_transform_factory as btf


# from .interactive import ConnectionMixin, mpl_connect
from graphical.draggables.machinery import DragMachinery
from recipes.iter import flatiter

from IPython import embed


# from decor import expose

def picker(artist, event):
    # print(vars(event))
    mouse_position = (event.xdata, event.ydata)
    if None in mouse_position:
        return False, {}

    ax = artist.axes
    _data2ax_trans = ax.transData + ax.transAxes.inverted()
    mouse_ax_pos = _data2ax_trans.transform(mouse_position)

    centre = artist.get_centre()

    prox = np.linalg.norm(mouse_ax_pos - centre)
    hit = prox < 0.5
    print('mouse_position, mouse_ax_pos,  centre')
    print(mouse_position, mouse_ax_pos, centre)
    print('prox', prox)
    print('hit', hit)
    return hit, {}


# ****************************************************************************************************
class AxesSliders(DragMachinery):
    """
    Class with sliders that set min/max of a value

    Basic interactions include:
        movement - click & drag
        reset - middle mouse

    Connect listeners to the sliders with
    sliders.upper.on_changed.add(func)
    """

    delta_min = 0.025
    _use_positions = slice(None)  # indices of the draggable objects that can

    # be set by assigning to the `positions` attribute

    # marker_size = 10
    # valfmt = '%1.2f',

    def __init__(self, ax, positions, slide_axis='x', dragging=True,
                 trapped=False, annotate=False, haunted=False, use_blit=True,
                 extra_markers=(),
                 **props):
        """

        Parameters
        ----------
        ax
        positions
        slide_axis
        dragging
        trapped
        annotate
        haunted
        use_blit
        extra_markers:
            additional markers per line for aesthetic
        props:
            dict of properties for the lines. each property is a 2-tuple
        """

        self._ax = ax
        # initial values
        self.slide_axis = slide_axis.lower()
        self._ifree = i = int(slide_axis == 'y')
        # `self._ifree`: 0 for x-axis slider, 1 for y-axis
        self._ilock = int(not bool(i))
        self._locked = 'yx'[i]
        self._order = o = slice(None, None, [1, -1][i])

        # check positions
        # assert np.size(positions) == 2, 'Positions should have size 2'
        self._original_position = positions  # np.sort(

        if props:
            prop_cycle = cycler(**props)
        else:
            prop_cycle = [{}] * len(self._original_position)

        # get transform (like axhline / axvline)
        get_transform = getattr(ax, 'get_%saxis_transform' % self.slide_axis)
        transform = get_transform(which='grid')

        # create the dragging UI
        DragMachinery.__init__(self, use_blit=use_blit)

        # add the sliding lines
        sliders = []
        nem = len(extra_markers)
        clip_on = use_blit or trapped
        for pos, props in zip(self._original_position, prop_cycle):
            # create sliders Line2D
            x, y = [[pos], [0, 1]][o]
            line = Line2D(x, y, transform=transform, clip_on=clip_on, **props)
            ax.add_artist(line)
            dart = self.add_artist(line, (0, 0), annotate, haunted,
                                   trapped=trapped)
            sliders.append(line)

            # add some markers for aesthetic
            for x, m in zip(np.linspace(0, 1, nem, 1), extra_markers):  # '>s<'

                x, y = [[pos], [x]][o]
                linked = Line2D(x, y, color=props['color'], marker=m,
                                transform=transform, clip_on=clip_on)
                ax.add_line(linked)  # move to link function??
                self[line].link(linked)

        # set upper / lower attributes for convenience
        self.lower = self.draggables[sliders[0]]
        self.upper = self.draggables[sliders[1]]
        self.lock(self._locked)

        # constrain movement
        x0, x1 = self._original_position[:2]
        self.lower.ymax = x1 - self.delta_min
        self.upper.ymin = x0 + self.delta_min

        self.upper.on_changed.add(self.set_lower_ymax)
        self.lower.on_changed.add(self.set_upper_ymin)

        self.dragging = dragging
        # FIXME: get this working to you update on release not motion for speed
        # create sliders & add to axis

    @property
    def positions(self):
        return self._original_position[self._use_positions] + \
               self.offsets[self._use_positions, self._ifree]

    def set_positions(self, values, draw_on=True):
        # not a property since it returns a list of artists to draw
        # assert len(values) == len(self.artists)
        draw_list = []
        for drg, v in zip(self.draggables.values(), values):
            new = (v, drg.position[self._ilock])[self._order]
            art = self.update(drg, new, False)
            draw_list.extend(art)
            # avoid drawing here with `draw_on=False`

        if draw_on:
            self.draw(draw_list)
        return draw_list

    def set_upper_ymin(self, x, y):
        # pos = self.get_positions()
        self.upper.ymin = y + self.delta_min
        logging.debug('upper ymin: %.2f, %.2f', self.upper.ymin, y)

    def set_lower_ymax(self, x, y):
        # pos = self.get_positions()
        self.lower.ymax = y - self.delta_min
        logging.debug('lower ymax: %.2f, %.2f', self.lower.ymax, y)

    def setup_axes(self, ax):
        """ """
        ax.set_navigate(False)  # turn off nav for this axis


class TripleSliders(AxesSliders):  # MinMaxMeanSliders
    # FIXME: middle slider doesn't always drag the range.....

    """
    A set of 3 sliders for setting min/max/mean value.  Middle slider is
    linked to both the upper and lower slider and will move both those when
    changed.  This allows for easily altering the upper/lower range values
    simultaneously.  The middle slider will also always be at the mean
    position of the upper/lower sliders.
    """
    _use_positions = [0, 1]

    def __init__(self, ax, positions, slide_axis='x', dragging=True,
                 trapped=False, annotate=False, haunted=False, use_blit=True,
                 extra_markers=(), **props):
        """

        Parameters
        ----------
        ax
        x0
        x1
        slide_axis
        dragging
        trapped
        annotate
        haunted
        use_blit
        kwargs
        """

        xc = np.mean(positions)
        pos3 = np.hstack([positions, xc])

        AxesSliders.__init__(self, ax, pos3, slide_axis, dragging, trapped,
                             annotate, haunted, use_blit, extra_markers,
                             **props)
        #
        self.centre = self.draggables[2]
        self.centre.lock(self._locked)
        # self.lower.on_picked.add(lambda x, y: self.centre.set_animate(True))

        # add method to move central slider when either other is moved
        self._lwr_mv_ctr = self.lower.on_changed.add(self.set_centre)
        self._upr_mv_ctr = self.upper.on_changed.add(self.set_centre)

        # make sure centre slide is between upper and lower
        self.lower.on_release.add(self.set_centre_max)
        self.upper.on_release.add(self.set_centre_min)

        # disconnect links to centre to avoid infinite recursion
        self.centre.on_picked.add(self.deactivate_centre_control)

        # make sure wo draw all the linked artists on center move
        self.centre.on_changed.add(
                lambda x, y: self.lower.draw_list + self.upper.draw_list)

        # re-link to the centre slider
        self.centre.on_release.add(self.activate_centre_control)

    def set_centre(self, x, y):
        """
        set the position of the central slider when either of the other sliders
        is moved
        """
        y = self.positions.mean()
        draw_list = self.centre.update(x, y)
        return draw_list

    def set_centre_min(self, x, y):
        """set minimum position of the central slider"""
        self.centre.ymin = self.lower.ymin + self.delta_min / 2
        logging.debug('centre min: %.2f, %.2f', self.centre.ymin, y)

    def set_centre_max(self, x, y):
        """set maximum position of the central slider"""
        self.centre.ymax = self.upper.ymax + self.delta_min / 2
        logging.debug('centre ymax: %.2f, %.2f', self.centre.ymax, y)

    def _animate(self, b):
        for drg in self.draggables.values():
            drg.set_animated(b)

    def animate(self, x, y):
        self._animate(True)

    def deanimate(self, x, y):
        self._animate(False)

    def centre_moves(self, x, y):
        up = self.delta[self._ifree] > 0  # True if movement is upwards
        cpos = self.centre.position  # previous position
        art1 = self.centre.update(x, y)
        shift = self.centre.position - cpos
        # print(shift, self.delta)

        # upper if moving up else lower. i.e. the one that may get clipped
        lead = self.draggables[int(up)]
        lpos = lead.position + shift
        art2 = lead.update(*lpos)

        trail = self.draggables[int(not up)]
        tpos = 2 * self.centre.position - lead.position
        art3 = trail.update(*tpos)

        return art1 + art2 + art3

    def activate_centre_control(self, x, y):
        # print('act')
        self.lower.on_changed.active[self._lwr_mv_ctr] = True
        self.upper.on_changed.active[self._upr_mv_ctr] = True

    def deactivate_centre_control(self, x, y):
        # print('deact')
        self.lower.on_changed.active[self._lwr_mv_ctr] = False
        self.upper.on_changed.active[self._upr_mv_ctr] = False

    # def on_pick(self, event):
    #     if self._ignore_pick(event):
    #         return
    #
    #     self.centre.set_animated(True)
    #     AxesSliders.on_pick(self, event)

    def on_motion(self, event):

        # AxesSliders.on_motion(self, event)

        if event.button != 1:
            return

        if self.selection:
            draggable = self.draggables[self.selection]

            xydisp = event.x, event.y
            xydata = x, y = self.ax.transData.inverted().transform(xydisp)
            self.delta = xydata - self.ref_point

            # TODO: find a way of using this conditional logic in the update method??
            if draggable is self.centre:
                draw_list = self.centre_moves(x, y)
                self.draw(draw_list)
            else:
                self.update(draggable, xydata)

    def on_release(self, event):
        if event.button != 1:
            return

        if self.selection:
            logging.debug('on_release: %r', self.selection)
            # Remove dragging method for selected artist
            self.remove_connection('motion_notify_event')

            xydisp = event.x, event.y  # NOTE: may be far outside allowed range
            x, y = self.ax.transData.inverted().transform(xydisp)  # xydata =
            logging.debug('on_release: delta %s', self.delta)

            draggable = self.draggables[self.selection]
            draw_list = draggable.on_release(x, y)

            if draggable is self.centre:
                draw_list = self.centre_moves(x, y)

            logging.debug('on_release: offset %s %s', draggable,
                          draggable.offset)

            if self.use_blit:
                self.draw_blit(draw_list)
                for art in filter(None, flatiter(draw_list)):
                    art.set_animated(False)

        self.selection = None

    def reset(self):
        # super().reset()
        logging.debug('resetting!')
        draw_list = []
        for draggable, off in zip(self.draggables.values(),
                                  self._original_offsets):
            artists = draggable.update(*draggable.ref_point)
            draw_list.extend(artists)

        # artist = self.centre_moves(*self.centre.position)
        self.draw(draw_list)
