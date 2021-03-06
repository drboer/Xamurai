import sys, os
from PyQt4.QtGui import QApplication
from fullGUI.mainWindow import MainWindow


def userdir(hint1='', hint2='', hint3=''):
    '''
    Gives a list with the absolute paths of all user directories containing 1,2, or 3 substrings
    It only looks for directories in /beamlines/bl13/projects/cycleXXXX
    '''
    directories=[]
    topdir = '/beamlines/bl13/projects/'

#    dir_cycles = filter(lambda s: s.startswith('cycle'), os.listdir(topdir))
    dir_cycles = filter(lambda s: 'cycle20' in s and '-' not in s, os.listdir(topdir))

    for cycle in dir_cycles:
        cyclepath = topdir+cycle+'/'
        dirs_in_cycle = filter(lambda s: hint1 in s and hint2 in s and hint3 in s, os.listdir(cyclepath))
        absdirs_in_cycle = [cyclepath+s for s in dirs_in_cycle]
        directories = directories + absdirs_in_cycle

    return directories

def latest_projectdir(hint1 = ''):
    if hint1 == '':
        return ''
    else:
        userdirout = userdir(hint1)

        if len(userdirout) == 1:
            return ''
        else:
            latestdir = ''
            for line in userdirout:
                if 'cycle' in line:  # last line of userdir output is a summary, no cycle in line, discard
                    if line > latestdir: # get latest date by looking at the directory name
                        latestdir = line
            return latestdir

def latest_userdir(projectdir = ''):
    if projectdir:
        latestdir = os.path.join(projectdir, 'DATA')
        latdatadir = '0000000'
        for datadir in os.listdir(latestdir):
            if datadir.isdigit() and datadir > latdatadir:
                latdatadir = datadir
        latestdir = os.path.join(latestdir, latdatadir)
        return latestdir
    else: return ''

def lastdateUserDir(hint):
    if hint:
        print 'lastdateUserDir: hint %s' % hint
        latestdir = latest_projectdir(hint)
        print 'lastdateUserDir: projectdir %s' % latestdir
        return latest_userdir(latestdir)
    else: return ''

def datadirFromArgument(hint):
    # TODO: based on userdir argument, find latest dataset file and update the dataset list
    # Determine userdir
    #print '%d arguments[0] %s' % (len(args), args[0])
    latestdir = ''
    
    latestdir = lastdateUserDir(hint)
    if latestdir == '' or latestdir == None:
            if os.path.isdir(hint):
                latestdir = str(hint)
            else:
                print 'Sorry, cant interpret the first argument given to the script as a directory' 

    return latestdir

def manproc_main(argv):
  
    print 'Defining main window' 
    app = QApplication(sys.argv)
    args = app.arguments()

    print 'Defining main window' 
    
    win = MainWindow(app)

    latestdir = ''
    if len(args) > 1: 
        latestdir = datadirFromArgument(str(args[1]))
    else:
        latestdir = os.getcwd().replace('/storagebls','')
    
    
    if latestdir:
        print 'The user dir is: %s' % latestdir
        win.directory.setText(latestdir)
        win.scanRootDirectory(True)

    # Position on screen
    win.move(80, 80)
    win.info.move(1120+10+80, 80)
    win.jobs.move(1120+10+80, 400+40+80)
    # Show
    win.show()

    app.exec_()


if __name__ == "__main__":
    sys.exit(manproc_main(sys.argv[1:]))
