import fullGUI.phaserGUI as Gui
import sys

# App variable
app = Gui.QApplication(sys.argv)
# Starting GUI
form = Gui.PhaserForm(app)
# START
app.exec_()
