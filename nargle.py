#!/usr/bin/python
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
def filerefresh(filename=None, action='add', newname=None):
    global list_of_files, files
    list_of_files = os.listdir(path)
    list_of_files = [os.path.splitext(i)[0] for i in list_of_files if os.path.splitext(i)[1] == ".txt"]
    def readfile(filename):
        this_path = path + '/' + filename + '.txt'
        if os.path.isfile(this_path):
            fd = open(this_path)
            files[filename] = fd.read()
            fd.close()
    if filename:
        if action == 'remove':
            del files[filename]
        elif action == 'rename':
            files[newname] = files[filename]
            del files[filename]
        else:
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
commands = {'q': 'raise urwid.ExitMainLoop()',
            'quit': ':q',
            'delete': ':d',
            'd': 'deleteorrenamefile()',
}
searchstring = ''
errorstring = ':q to quit, :d to delete a file' 
errormode = True
currentfilename = False
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
        incsearch()
    elif key == "enter":
        currentfilename = searchstring
        createfile(searchstring)
        col.focus_position = 1
    elif key == "right":
            currentfilename = lb.curtext()
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
    newword = re.escape(word) 
    for i in viewable_list_of_files:
        if re.search(newword, i, re.I) or re.search(newword, files[i], re.I):
            returnlist.append(i)
    return returnlist


def createfile(filename):
    global files, viewable_list_of_files
    this_path = path + "/" + filename + ".txt"
    fd = open(this_path, 'a')
    fd.close()
    filerefresh(filename)
    files[filename] = ''
    viewable_list_of_files = [filename]
    updatelist()
    setedittolistitem(lb.curtext()) 
    

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

def deleteorrenamefile(newname=None):
    global currentfilename
    currentfilename = lb.curtext()
    this_path = path + "/" + currentfilename + '.txt'
    if newname:
        new_path = path + "/" + newname + '.txt'
        os.rename(this_path, new_path)
        filerefresh(currentfilename, 'rename', newname)
    else:
        os.remove(this_path)
        filerefresh(currentfilename, 'remove')    
    incsearch()

def updatelist():
    for i in range(len(sflw)):
        del sflw[0]
    for i in sorted(viewable_list_of_files):
        sflw.append(urwid.AttrMap(SText(i, wrap='clip'), 'inversegreen', focus_map='boldgreen'))
        
        
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
        global errormode
        if key in ["up", "down", "page up", "page down"]:
            super().keypress(size, key)
            setedittolistitem(self.curtext())
            errormode = False
            updateheader()
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
    this_path = path + '/' + currentfilename + '.txt'
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
header = urwid.Text('')
footer = urwid.Text('', align='right')
frame = urwid.Frame(col, header, footer)


#---INITIALISE, DEFINE A MAIN LOOP, AND RUN---
# initialisation
palette = [('boldgreen', 'black,bold', 'dark green'),
           ('inversegreen', 'dark green,bold', 'black'),]
updateheader()
setedittolistitem(lb.curtext())
# define loop and run
loop = urwid.MainLoop(frame, palette, unhandled_input=handleinput, screen=urwid.raw_display.Screen(), handle_mouse=False)
loop.run()

