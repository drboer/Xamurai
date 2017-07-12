from PyQt4.QtGui import QLabel, QWidget, QSpinBox, QHBoxLayout, QPalette, QColor


# MINOR WIDGETS
class QLineInfo(QLabel):
    def __init__(self, prefix="", suffix="", string="", parent=None):
        super(QLineInfo, self).__init__(parent)
        self.prefix = prefix
        self.suffix = suffix
        self.setText(string)

    def setText(self, string):
        mod_string = self.prefix + string + self.suffix
        super(QLineInfo, self).setText(mod_string)

    def getText(self):
        text = self.text().replace(self.prefix, "", 1).replace(self.suffix, "", 1)
        return str(text)


class CustomObj:
    def __init__(self): pass


def num_widget():
    widget = QWidget()
    label = QLabel("Number in ASU")
    label.setToolTip("Number of times this item appears in the asymmetric unit")
    widget.num_box = QSpinBox()
    widget.num_box.setRange(1, 50)
    layout = QHBoxLayout()
    layout.addWidget(label)
    layout.addWidget(widget.num_box)
    layout.addStretch()
    layout.setMargin(0)
    widget.setLayout(layout)
    return widget


def IDENSelector():
    id_selector = QSpinBox()
    id_selector.setRange(1, 99)
    id_selector.setSingleStep(1)
    id_selector.setValue(50)
    return id_selector


# MINOR LAYOUT FUNCTIONS
def set_color(qt_wid, r, g, b, a=255):
    palette = QPalette()
    palette.setColor(QPalette.Base, QColor(r, g, b, a))
    qt_wid.setPalette(palette)


def colorize(string, color):
    return "<font color=\"" + color + "\">" + string + "</font>"
