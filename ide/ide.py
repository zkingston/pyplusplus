#!/usr/bin/env python
#Boa:App:BoaApp

# Copyright 2007 Alexander Eisenhuth
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# http://www.boost.org/LICENSE_1_0.txt)

""" """

import wx

from views.main_frame import create as createMainFrame
from controllers.main import MainController

modules ={u'main controller': [0, '', u'controllers/main.py'],
 u'main view': [1, 'Main frame of ide', u'views/main_frame.py']}

class BoaApp(wx.App):
    def OnInit(self):
     
        self.main = createMainFrame(None)
        
        # Instanciate main controller and give it to the main view
        controller = MainController(self.main)
        self.main.set_controller(controller)
        
        self.main.Show()
        self.SetTopWindow(self.main)
        return True

def main():
    application = BoaApp(0)
    application.MainLoop()

if __name__ == '__main__':
    main()
