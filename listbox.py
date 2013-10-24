import urwid
import time
import os
import os.path
import re
import sys

#---HANDLE CONMAND LINE ARGUMENTS---        
if len(sys.argv) == 1:
    #set the path to get notes from.
    path = os.environ["HOME"] + "/Dropbox/plain text" 
elif len(sys.argv) == 2:
    path = sys.argv[1]
else:
    print(usage)
    exit()

    
#---READ IN A LIST OF FILES---
def filerefresh(filename=None):
    global list_of_files, files
    list_of_files = os.listdir(path)
    def readfile(name):
        this_path = path + "/" + name
        if os.path.isfile(this_path):
            fd = open(this_path)
            files[name] = fd.read()
            fd.close()
    if filename:
        readfile(filename)
    else:
        files = {}
        for name in list_of_files:
            readfile(name)
filerefresh()
viewable_list_of_files = list_of_files
 

#---DEAL WITH INPUT---
commandmode = False
commandstring = ''
# A dict of commands and the corresponding python code they run
# Code starting with ':' is instead interpreted as meaning an alias
#      to another command
commands = {'q': 'raise urwid.ExitMainLoop()', 'quit':':q'}
searchstring = ''
errorstring = 'To see help, type :h' #TODO
errormode = True
def handleinput(key):
    global commandstring, commandmode, errormode, searchstring
    #Before processing
    errormode = False
    #Processing - enter and leave modes, and pass keys to the
    #           - functions for those modes
    if key == ":":
        commandmode = True
        commandstring = ":"
    elif key == "esc":
        commandmode = False
        frame.focus_position = 'body'
        if col.focus_position == 0:
            searchstring = ''
            incsearch()
        col.focus_position = 0
    elif commandmode:
        handlecommandinput(key)
    else:
        handlesearchinput(key)
    #After processing
    updateheader()
    updatefooter()
        
def handlesearchinput(key):
    global searchstring, currentfilename
    if key == ' ':
        if searchstring and searchstring[-1] != ' ':
            searchstring += key
    elif key in ['backspace', 'delete']:
        if searchstring and searchstring[-1] == ' ':
            searchstring = searchstring[:-1]
        searchstring = searchstring[:-1]
    elif key == "enter":
        if lb.focus:
            currentfilename = lb.curtext()
        else:
            currentfilename = searchstring
            createfile(searchstring)
        col.focus_position = 1
    elif len(key) == 1:
        searchstring += key
    incsearch()

def incsearch():
    global viewable_list_of_files
    viewable_list_of_files = list_of_files
    for word in searchstring.split():
        viewable_list_of_files = [i for i in viewable_list_of_files if i in matchingfiles(word)]
    updatelist()
    setedittolistitem(lb.curtext()) 

def matchingfiles(word):
    returnlist = []
    for i in list_of_files:
        if re.search(word, i, re.I):
            returnlist.append(i)
    return returnlist


def createfile(name):
    this_path = path + "/" + name
    fd = open(this_path, 'a')
    fd.close()
    filerefresh(name)
    
    

def handlecommandinput(key):
    global commandstring, commandmode
    if key == "enter":
        commandmode = False
        processcommand()
    elif key in ["backspace", "delete"]:
        commandstring = commandstring[:-1]
    elif key == ' ':
        pass
    elif len(key) == 1:
        commandstring += key

def processcommand():
    global commandstring, errormode, errorstring
    if commandstring[0] == ':':
        commandstring = commandstring[1:]
    try:
        commandcode = commands[commandstring] or None
    except KeyError:
        errormode = True
        errorstring = "Error: Invalid Command"
        return
    if commandcode[0] == ':':
        commandstring = commandcode
        processcommand()
    else:
        exec(commandcode)
    
def updatelist():
    for i in range(len(sflw)):
        del sflw[0]
    for i in sorted(viewable_list_of_files):
        sflw.append(urwid.AttrMap(SText(i, wrap='clip'), 'inverse', focus_map='mrbold'))
        
        
def updateheader():
    if commandmode:
        header.set_text(commandstring)
    elif errormode:
        header.set_text(errorstring)
    else:
        header.set_text(searchstring)

def updatefooter():
    listtext = lb.curtext()
    if listtext:
        footer.set_text(listtext)
    else:
        footer.set_text(searchstring)
       
#---CREATE CUSTOM WIDGET CLASSES---
# A selectable text class
class SText(urwid.Text):
    _selectable = True
    def keypress(self, size, key):
        return key #Let parent widget deal with processing keys

# A listbox that sends a signal after processing keypresses
class KListBox(urwid.ListBox):
    def keypress(self, size, key):
        if key in ["up", "down", "page up", "page down"]:
            super().keypress(size, key)
            setedittolistitem(self.curtext())
            updatefooter()
        else:
            handleinput(key)
    def curtext(self):
        if self.focus:
            text = self.focus.base_widget.get_text()[0]
            return text
        else:
            return False
# on listchange signal
def setedittolistitem(text):
    if lb.focus:
        editable.set_edit_text(files[text])
    else:
        editable.set_edit_text("Nothing to see here.")

# An edit box that can insert newlines
class BEdit(urwid.Edit):
    def keypress(self, size, key):
        if key == 'enter':
            super().insert_text('\n')
        elif key == 'esc':
            savecurrentfile()
            filerefresh(currentfilename)
            handleinput(key)
        else:
            super().keypress(size, key)

def savecurrentfile():
    this_path = path + "/" + currentfilename
    if os.path.isfile(this_path):
        fd = open(this_path, 'w')
        editedtext = editable.get_edit_text()
        fd.write(editedtext)
        fd.close()


        
#---CREATE A LISTBOX OF TEXT WIDGETS FROM THAT LIST---
sflw = urwid.SimpleFocusListWalker([])
updatelist()
lb = KListBox(sflw)


#---CREATE A COLUMN WIDGET CONTAINING THE LISTBOX AND EDIT WIDGETS---
editable = BEdit()
fill = urwid.Filler(editable, valign='top')
collist = [('weight', 1, lb), ('weight', 2, fill)]
col = urwid.Columns(collist, dividechars=2, min_width=15)


#---PUT THE COLUMN IN A FRAME---
header = urwid.Text(commandstring)
footer = urwid.Text(('mrbold', "Footer"), align='right')
frame = urwid.Frame(col, header, footer)


#---INITIALISE, DEFINE A MAIN LOOP, AND RUN---
# initialisation
palette = [('mrbold', 'bold', '', 'bold'),
           ('inverse', 'black,bold', 'dark green'),]

setedittolistitem(lb.curtext())
# define loop and run
loop = urwid.MainLoop(frame, palette, unhandled_input=handleinput, screen=urwid.raw_display.Screen())
loop.run()

