from subprocess import Popen, PIPE


def now():
    p = Popen(["date", "+\"%d %b %Y %H:%M:%S\""], stdout=PIPE)
    p.wait()
    return p.communicate()[0].replace("\n", "").replace("\"", "")

    
def update_maximum(widget, ref_widget=""):
    def func():
        value = ref_widget.value()
        if value < widget.value():
            widget.setValue(value)
    return func

    
def update_minimum(widget, ref_widget=""):
    def func():
        value = ref_widget.value()
        if value > widget.value():
            widget.setValue(value)
    return func