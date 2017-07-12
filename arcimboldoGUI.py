import fullGUI.arcimboldoGUI as Gui
import sys

# App variable
app = Gui.QApplication(sys.argv)
# Starting GUI
form = Gui.ArcimboldoForm(app)
# START
app.exec_()
