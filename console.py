import re

from Tkinter import Frame, Button, Label, Text, Scrollbar, Canvas, Wm, READABLE

from mininet.log import setLogLevel
from mininet.term import makeTerms, cleanUpScreens
from mininet.util import quietRun

class Console(Frame):
    "A simple console on a host."

    def __init__(self, parent, net, node, height=10, width=32, title='Node'):
        Frame.__init__(self, parent)

        self.net = net
        self.node = node
        self.prompt = node.name + '# '
        self.height, self.width, self.title = height, width, title

        # Initialize widget styles
        self.buttonStyle = {'font': 'Monaco 7 bold', 'fg':'white', 'bg': 'grey15',
                            'activeforeground':'green2', 'activebackground':'grey15'}
        self.textStyle = {
            'font': 'Monaco 7',
            'bg': 'black',
            'fg': 'green2',
            'width': self.width,
            'height': self.height,
            'relief': 'sunken',
            'insertbackground': 'green',
            'highlightcolor': 'green',
            'selectforeground': 'black',
            'selectbackground': 'green'
        }
        # Set up widgets
        self.text = self.makeWidgets()
        self.bindEvents()
        self.sendCmd('export TERM=dumb')

        self.outputHook = None

    def makeWidgets(self):
        "Make a label, a text area, and a scroll bar."

        def newTerm(net=self.net, node=self.node, title=self.title):
            "Pop up a new terminal window for a node."
            net.terms += makeTerms([node], title)
        label = Button(self, text=self.node.name, command=newTerm,
                        **self.buttonStyle)
        label.pack(side='top', fill='x')
        text = Text(self, wrap='word', **self.textStyle)
        ybar = Scrollbar(self, orient='vertical', width=7, command=text.yview, 
                         bg='grey15', activebackground='grey15')
        text.configure(yscrollcommand=ybar.set)
        text.pack(side='left', expand=True, fill='both')
        ybar.pack(side='right', fill='y')
        return text

    def bindEvents(self):
        "Bind keyboard and file events."
        # The text widget handles regular key presses, but we
        # use special handlers for the following:
        self.text.bind('<Return>', self.handleReturn)
        self.text.bind('<Control-c>', self.handleInt)
        self.text.bind('<KeyPress>', self.handleKey)
        # This is not well-documented, but it is the correct
        # way to trigger a file event handler from Tk's
        # event loop!
        self.tk.createfilehandler(self.node.stdout, READABLE,
                                  self.handleReadable)

    # We're not a terminal (yet?), so we ignore the following
    # control characters other than [\b\n\r]
    ignoreChars = re.compile(r'[\x00-\x07\x09\x0b\x0c\x0e-\x1f]+')

    def append(self, text):
        "Append something to our text frame."
        text = self.ignoreChars.sub('', text)
        self.text.insert('end', text)
        self.text.mark_set('insert', 'end')
        self.text.see('insert')
        outputHook = lambda x, y: True  # make pylint happier
        if self.outputHook:
            outputHook = self.outputHook
        outputHook(self, text)

    def handleKey(self, event):
        "If it's an interactive command, send it to the node."
        char = event.char
        if self.node.waiting:
            self.node.write(char)

    def handleReturn(self, event):
        "Handle a carriage return."
        cmd = self.text.get('insert linestart', 'insert lineend')
        # Send it immediately, if "interactive" command
        if self.node.waiting:
            self.node.write(event.char)
            return
        # Otherwise send the whole line to the shell
        pos = cmd.find(self.prompt)
        if pos >= 0:
            cmd = cmd[pos + len(self.prompt):]
        self.sendCmd(cmd)

    # Callback ignores event
    def handleInt(self, _event=None):
        "Handle control-c."
        self.node.sendInt()

    def sendCmd(self, cmd):
        "Send a command to our node."
        if not self.node.waiting:
            self.node.sendCmd(cmd)

    def handleReadable(self, _fds, timeoutms=None):
        "Handle file readable event."
        data = self.node.monitor(timeoutms)
        self.append(data)
        if not self.node.waiting:
            # Print prompt
            self.append(self.prompt)

    def waiting(self):
        "Are we waiting for output?"
        return self.node.waiting

    def waitOutput(self):
        "Wait for any remaining output."
        while self.node.waiting:
            # A bit of a trade-off here...
            self.handleReadable(self, timeoutms=1000)
            self.update()

    def clear(self):
        "Clear all of our text."
        self.text.delete('1.0', 'end')


class ConsoleApp(Frame):

    "Simple Tk consoles for Mininet."

    menuStyle = {'font': 'Geneva 7 bold', 'fg':'white', 'bg':'grey15', 
                 'activeforeground':'green2', 'activebackground':'grey15'}

    def __init__(self, net, parent=None, width=3):
        Frame.__init__(self, parent, bg='grey15')
        self.top = self.winfo_toplevel()
        self.top.title('Mininet')
        self.net = net
        self.menubar = self.createMenuBar()
        cframe = self.cframe = Frame(self)
        self.consoles = {}  # consoles themselves
        titles = {
            'hosts': 'Host',
            'switches': 'Switch',
            'controllers': 'Controller'
        }
        for name in titles:
            nodes = getattr(net, name)
            frame, consoles = self.createConsoles(cframe, nodes, width, titles[name])
            self.consoles[name] = Object(frame=frame, consoles=consoles)
        self.selected = None
        self.select('hosts')
        self.cframe.pack(expand=True, fill='both')
        cleanUpScreens()
        # Close window gracefully
        Wm.wm_protocol(self.top, name='WM_DELETE_WINDOW', func=self.quit)
        self.pack(expand=True, fill='both')

    def setOutputHook(self, fn=None, consoles=None):
        "Register fn as output hook [on specific consoles.]"
        if consoles is None:
            consoles = self.consoles['hosts'].consoles
        for console in consoles:
            console.outputHook = fn

    def createConsoles(self, parent, nodes, width, title):
        "Create a grid of consoles in a frame."
        f = Frame(parent)
        # Create consoles
        consoles = []
        index = 0
        for node in nodes:
            console = Console(f, self.net, node, title=title)
            consoles.append(console)
            row = index / width
            column = index % width
            console.grid(row=row, column=column, sticky='nsew')
            index += 1
            f.rowconfigure(row, weight=1)
            f.columnconfigure(column, weight=1)
        return f, consoles

    def select(self, groupName):
        "Select a group of consoles to display."
        if self.selected is not None:
            self.selected.frame.pack_forget()
        self.selected = self.consoles[ groupName ]
        self.selected.frame.pack(expand=True, fill='both')

    def createMenuBar(self):
        "Create and return a menu (really button) bar."
        f = Frame(self)
        buttons = [
            ('Hosts', lambda: self.select('hosts')),
            ('Switches', lambda: self.select('switches')),
            ('Controllers', lambda: self.select('controllers')),
            ('Ping', self.ping),
            ('Iperf', self.iperf),
            ('Interrupt', self.stop),
            ('Clear', self.clear),
            ('Quit', self.quit)
        ]
        for name, cmd in buttons:
            b = Button(f, text=name, command=cmd, **self.menuStyle)
            b.pack(side='left')
        f.pack(padx=4, pady=4, fill='x')
        return f

    def clear(self):
        "Clear selection."
        for console in self.selected.consoles:
            console.clear()

    def waiting( self, consoles=None ):
        "Are any of our hosts waiting for output?"
        if consoles is None:
            consoles = self.consoles[ 'hosts' ].consoles
        for console in consoles:
            if console.waiting():
                return True
        return False

    def ping( self ):
        "Tell each host to ping the next one."
        consoles = self.consoles[ 'hosts' ].consoles
        if self.waiting( consoles ):
            return
        count = len( consoles )
        i = 0
        for console in consoles:
            i = ( i + 1 ) % count
            ip = consoles[ i ].node.IP()
            console.sendCmd( 'ping ' + ip )

    def iperf( self ):
        "Tell each host to iperf to the next one."
        consoles = self.consoles[ 'hosts' ].consoles
        if self.waiting( consoles ):
            return
        count = len( consoles )
        # self.setOutputHook( self.updateGraph )
        for console in consoles:
            # Sometimes iperf -sD doesn't return,
            # so we run it in the background instead
            console.node.cmd( 'iperf -s &' )
        i = 0
        for console in consoles:
            i = ( i + 1 ) % count
            ip = consoles[ i ].node.IP()
            console.sendCmd( 'iperf -t 99999 -i 1 -c ' + ip )

    def stop( self, wait=True ):
        "Interrupt all hosts."
        consoles = self.consoles[ 'hosts' ].consoles
        for console in consoles:
            console.handleInt()
        if wait:
            for console in consoles:
                console.waitOutput()
        self.setOutputHook( None )
        # Shut down any iperfs that might still be running
        quietRun( 'killall -9 iperf' )

    def quit( self ):
        "Stop everything and quit."
        self.stop( wait=False)
        Frame.quit( self )


# Make it easier to construct and assign objects
def assign( obj, **kwargs ):
    "Set a bunch of fields in an object."
    obj.__dict__.update( kwargs )

class Object( object ):
    "Generic object you can stuff junk into."
    def __init__( self, **kwargs ):
        assign( self, **kwargs )