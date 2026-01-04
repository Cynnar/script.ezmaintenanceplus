import xbmc
import xbmcaddon
import xbmcgui
import os

# --- Constants ---
ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = ADDON.getAddonInfo('path')
MODULE_NAME = 'Log Viewer'
DIALOG = xbmcgui.Dialog()

# --- Globals (State for the Window) ---
# We use these to pass data into the WindowXML class instance
current_contents = ''
current_path = ''

class Viewer(xbmcgui.WindowXML):
    def __init__(self, strXMLname, strFallbackPath):
        super().__init__(strXMLname, strFallbackPath)
        
        # Key Codes for Exit (Back, Previous Menu)
        self.action_exit_keys = [10, 92]

        # XML Control IDs (Must match textview-skin.xml)
        self.title_box_control = 20301
        self.content_box_control = 20302
        self.scroll_bar = 20212
        self.refresh_button = 20293

    def onInit(self):
        # Set Title
        try:
            self.getControl(self.title_box_control).setText(f"{ADDON_NAME} - {MODULE_NAME}")
        except: pass

        # Set Content
        try:
            self.getControl(self.content_box_control).setText(current_contents)
        except: pass

        # Set initial focus to scrollbar so user can scroll immediately
        try:
            self.setFocusId(self.scroll_bar)
        except: pass

    def onAction(self, action):
        # Handle Back or Previous Menu
        if action.getId() in self.action_exit_keys:
            self.close()

    def onClick(self, control_id):
        # Handle Refresh Button
        if control_id == self.refresh_button:
            self.close()
            # Reload the view
            text_view(current_path)

def text_view(loc='', data=''):
    global current_contents
    global current_path
    
    current_contents = ''
    current_path = loc

    # Validate inputs
    if not loc and not data:
        return

    # Case 1: Load from File Path
    if loc and not data:
        if loc.lower().startswith('http'):
            DIALOG.ok(ADDON_NAME, 'Remote URL viewing not supported yet.')
            return
            
        if not os.path.exists(loc):
            DIALOG.ok(ADDON_NAME, f'File not found:\n{loc}')
            return

        try:
            # Open with 'ignore' to skip unreadable characters in logs (Fixes crashes)
            with open(loc, 'r', encoding='utf-8', errors='ignore') as f:
                current_contents = f.read()
        except Exception as e:
            DIALOG.ok(ADDON_NAME, f"Error reading file:\n{str(e)}")
            return

    # Case 2: Load from Data string directly
    elif data:
        current_contents = data

    # Empty check
    if not current_contents:
        DIALOG.ok(ADDON_NAME, 'The file is empty.')
        return

    # Colorize Errors and Warnings for better readability
    current_contents = current_contents.replace(' ERROR: ', ' [COLOR red]ERROR[/COLOR]: ')
    current_contents = current_contents.replace(' WARNING: ', ' [COLOR gold]WARNING[/COLOR]: ')

    # Launch the Window
    # Note: 'textview-skin.xml' must exist in your resources/skins/ folder
    win = Viewer('textview-skin.xml', ADDON_PATH)
    win.doModal()
    del win