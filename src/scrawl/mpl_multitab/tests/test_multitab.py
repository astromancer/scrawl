# std
import sys

# third-party
import numpy as np
from matplotlib import pylab as plt

# local
from scrawl.multitab import MplMultiTab, QtWidgets


# def test_multitab():
# fig, ax = plt.subplots()
# ax.plot(np.random.randn(100, 2), 'mp')

# fig2, ax2 = plt.subplots()
# ax2.plot(np.random.randn(100, 2), 'bx')

# ui = MplMultiTab(None, [fig], [])
# ui.show()


# Example use


# if __name__ == '__main__':

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    n = 100
    colours = 'rgb'
    ui = MplMultiTab()
    for c in colours:
        fig, ax = plt.subplots()
        ax.scatter(*np.random.randn(2, n), color=c)
        ui.add_tab(fig, c)

    
    ui.show()
    sys.exit(app.exec_())