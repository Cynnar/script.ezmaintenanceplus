import xbmc
import xbmcaddon
import xbmcplugin
import xbmcgui
import xbmcvfs
import os

# --- Core Kodi Shortcuts ---
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = ADDON.getAddonInfo('path')
DIALOG = xbmcgui.Dialog()

# --- Path Translation (Modern) ---
translatePath = xbmcvfs.translatePath

# --- Standard Paths ---
HOME_PATH = translatePath('special://home/')
ADDON_HOME = translatePath(f'special://home/addons/{ADDON_ID}/')
USERDATA_PATH = translatePath('special://home/userdata/')
ADDON_DATA_PATH = translatePath(os.path.join(USERDATA_PATH, 'addon_data', ADDON_ID))
BACKUP_PATH = translatePath('special://home/backupdir/')
PACKAGES_PATH = translatePath('special://home/addons/packages/')

# --- Shortcut Functions ---

def setting(id):
    """Get a setting value."""
    return ADDON.getSetting(id)

def setSetting(id, value):
    """Set a setting value."""
    return ADDON.setSetting(id, value)

def lang(id):
    """Get localized string from addon strings.po."""
    return ADDON.getLocalizedString(id)

def addonInfo(id):
    """Get addon metadata."""
    return ADDON.getAddonInfo(id)

def execute(cmd):
    """Execute a Kodi built-in command."""
    xbmc.executebuiltin(cmd)

def sleep(ms):
    """Sleep for milliseconds."""
    xbmc.sleep(ms)

# --- UI Helpers ---

def addonIcon():
    return os.path.join(ADDON_HOME, 'icon.png')

def addonFanart():
    return os.path.join(ADDON_HOME, 'fanart.jpg')

def infoDialog(message, heading=ADDON_NAME, icon='', time=3000, sound=False):
    if not icon: icon = addonIcon()
    elif icon == 'INFO': icon = xbmcgui.NOTIFICATION_INFO
    elif icon == 'WARNING': icon = xbmcgui.NOTIFICATION_WARNING
    elif icon == 'ERROR': icon = xbmcgui.NOTIFICATION_ERROR
    
    DIALOG.notification(heading, message, icon, time, sound=sound)

def yesnoDialog(line1, line2='', line3='', heading=ADDON_NAME, nolabel='No', yeslabel='Yes'):
    # In Kodi 19+, yesno dialog only takes one main message argument, so we join them.
    message = f"{line1}\n{line2}\n{line3}".strip()
    return DIALOG.yesno(heading, message, nolabel=nolabel, yeslabel=yeslabel)

def selectDialog(list_items, heading=ADDON_NAME):
    return DIALOG.select(heading, list_items)

def openSettings(query=None):
    try:
        ADDON.openSettings()
    except:
        pass

def refresh():
    execute('Container.Refresh')

def busy():
    # Modern busy dialog handling
    execute('ActivateWindow(busydialognocancel)')

def idle():
    execute('Dialog.Close(busydialognocancel)')
    # Fallback for older skins/versions just in case
    execute('Dialog.Close(busydialog)')

# --- Directory & File Helpers (Wrappers for xbmcvfs) ---
deleteFile = xbmcvfs.delete
deleteDir = xbmcvfs.rmdir
listDir = xbmcvfs.listdir
makeDir = xbmcvfs.mkdir
exists = xbmcvfs.exists