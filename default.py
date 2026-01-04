import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
import os
import sys
import urllib.parse
import time
import requests
import shutil

# Import our cleaned maintenance module
from resources.lib.modules import maintenance

# NOTE: These modules likely still contain Python 2 code and will need updating next:
from resources.lib.modules import control, tools, wiz, logviewer

# --- Constants ---
ADDON_ID = 'script.ezmaintenanceplus'
ADDON = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME = "EZ Maintenance+"
TRANSLATE_PATH = xbmcvfs.translatePath

# Paths
ADDON_FANART = ADDON.getAddonInfo('fanart')
ADDON_ICON = ADDON.getAddonInfo('icon')
HOME_PATH = TRANSLATE_PATH('special://home/')
USERDATA_PATH = TRANSLATE_PATH('special://home/userdata')

# Exclusions for Fresh Start (Don't delete the addon itself!)
EXCLUDE_DIRS = [
    ADDON_ID, 
    'backupdir', 
    'script.module.requests', 
    'script.module.urllib3', 
    'script.module.chardet', 
    'script.module.idna', 
    'script.module.certifi'
]

def get_params():
    """Parses sys.argv to get parameters passed to the plugin."""
    param = {}
    args = sys.argv[2]
    if len(args) >= 2:
        cleaned_args = args.replace('?', '')
        if cleaned_args[len(cleaned_args)-1] == '/':
            cleaned_args = cleaned_args[:-1]
        param = dict(urllib.parse.parse_qsl(cleaned_args))
    return param

def create_directory_item(name, action, description, icon=None, fanart=None, url_param=None, is_folder=False):
    """Helper to create Kodi menu items."""
    if not icon: icon = ADDON_ICON
    if not fanart: fanart = ADDON_FANART
    
    # Build the URL for the plugin
    # We construct the query string manually or via urlencode
    query = {
        'action': action,
        'name': name,
        'description': description,
        'icon': icon,
        'fanart': fanart
    }
    if url_param:
        query['url'] = url_param
        
    url_str = f"{sys.argv[0]}?{urllib.parse.urlencode(query)}"
    
    # Create List Item
    li = xbmcgui.ListItem(name)
    li.setArt({'icon': icon, 'thumb': icon, 'fanart': fanart})
    li.setInfo('video', {'title': name, 'plot': description})
    
    return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url_str, listitem=li, isFolder=is_folder)

# --- MENUS ---

def MAIN_MENU():
    create_directory_item('[COLOR red][B]FRESH START[/B][/COLOR]', 'fresh_start', 'Wipe Kodi and start fresh', is_folder=False)
    create_directory_item('[COLOR lime][B]MY WIZARD[/B][/COLOR]', 'builds', 'Install Custom Builds', is_folder=True)
    create_directory_item('[COLOR white][B]BACKUP/RESTORE[/B][/COLOR]', 'backup_restore', 'Backup or Restore your setup', is_folder=False)
    
    create_directory_item('[COLOR white][B]MAINTENANCE[/B][/COLOR]', 'maintenance', 'Clear Cache, Packages, and Thumbnails', is_folder=True)
    create_directory_item('[COLOR white][B]ADVANCED SETTINGS (BUFFER)[/B][/COLOR]', 'adv_settings', 'Modify network buffer sizes', is_folder=False)
    create_directory_item('[COLOR white][B]LOG VIEWER/UPLOADER[/B][/COLOR]', 'log_tools', 'View or upload Kodi logs', is_folder=False)
    create_directory_item('[COLOR white][B]SPEEDTEST[/B][/COLOR]', 'speedtest', 'Test internet connection', is_folder=False)
    
    create_directory_item('[COLOR white][B]SETTINGS[/B][/COLOR]', 'settings', 'Configure Addon Settings', is_folder=False)
    
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def MAINTENANCE_MENU():
    # Show next scheduled cleanup
    next_ts = maintenance.getNextMaintenance()
    if next_ts > 0:
        time_str = time.strftime("%a, %d %b %Y %I:%M:%S %p %Z", time.localtime(next_ts))
        create_directory_item(f'Next Auto Cleanup: {time_str}', 'noop', 'Scheduled time', is_folder=False)
    
    create_directory_item('Clear Cache', 'clear_cache', 'Delete Cache & Temp files', is_folder=False)
    create_directory_item('Clear Packages', 'clear_packages', 'Delete installation packages', is_folder=False)
    create_directory_item('Clear Thumbnails', 'clear_thumbs', 'Delete thumbnails and texture DB', is_folder=False)
    
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def BUILDS_MENU():
    # Dynamically load up to 5 builds from settings
    for i in range(1, 6):
        if ADDON.getSetting(f'enable_wiz{i}') != 'false':
            name = ADDON.getSetting(f'name{i}')
            url = ADDON.getSetting(f'url{i}')
            img = ADDON.getSetting(f'img{i}')
            if name and url:
                create_directory_item(f'[COLOR lime][B][Wizard][/B][/COLOR] {name}', 'install_build', 'Install this build', icon=img, fanart=img, url_param=url, is_folder=False)
    
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

# --- ACTIONS ---

def FRESH_START():
    if not xbmcgui.Dialog().yesno(ADDON_NAME, 'Are you absolutely certain you want to wipe this install?\nAll addons EXCLUDING THIS WIZARD will be lost!', yeslabel='Yes', nolabel='No'):
        return

    # Warning for skin
    xbmcgui.Dialog().ok(ADDON_NAME, 'Before Proceeding ensuring you are on the default Kodi skin (Estuary).')
    
    # 1. Switch Skin (helper from wiz module)
    try:
        wiz.skinswap()
    except:
        pass

    # 2. Wipe Files
    dp = xbmcgui.DialogProgress()
    dp.create(ADDON_NAME, "Wiping Install\nPlease Wait...")
    
    # Clean file deletion loop
    for root, dirs, files in os.walk(HOME_PATH, topdown=True):
        # Modify dirs in-place to skip exclusions
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for name in files:
            try:
                os.remove(os.path.join(root, name))
            except: pass
            
        for name in dirs:
            try:
                # Use shutil to remove non-empty directories if needed, though topdown usually handles files first
                shutil.rmtree(os.path.join(root, name))
            except: pass

    dp.close()
    
    xbmcgui.Dialog().ok(ADDON_NAME, 'Wipe Successful. Kodi will now reload.')
    xbmc.executebuiltin('LoadProfile(Master user)')

# --- ENTRY POINT ---

params = get_params()
action = params.get('action')
url = params.get('url')

if action is None:
    MAIN_MENU()

elif action == 'settings':
    ADDON.openSettings()

elif action == 'maintenance':
    MAINTENANCE_MENU()

elif action == 'clear_cache':
    maintenance.clearCache()
    xbmc.executebuiltin('Container.Refresh') # Refresh GUI

elif action == 'clear_packages':
    maintenance.purgePackages()

elif action == 'clear_thumbs':
    maintenance.deleteThumbnails()

elif action == 'fresh_start':
    FRESH_START()

elif action == 'builds':
    BUILDS_MENU()

elif action == 'adv_settings':
    tools.advancedSettings()

elif action == 'log_tools':
    logviewer.logView()

elif action == 'backup_restore':
    # This logic relies on wiz.py. 
    # Warning: If wiz.py is old, this might crash.
    types = ['BACKUP', 'RESTORE']
    sel = xbmcgui.Dialog().select("Select Action", types)
    if sel == 0: # Backup
        modes = ['Full Backup', 'Addons Settings']
        sel_mode = xbmcgui.Dialog().select("Backup Type", modes)
        if sel_mode == 0: wiz.backup(mode='full')
        elif sel_mode == 1: wiz.backup(mode='userdata')
    elif sel == 1: # Restore
        wiz.restoreFolder()

elif action == 'install_build':
    if url:
        # Check if user wants a fresh start first
        if xbmcgui.Dialog().yesno(ADDON_NAME, 'Fresh Start before installing?'):
            FRESH_START()
        wiz.buildInstaller(url)

elif action == 'speedtest':
    # Launch the speedtest script
    script_path = os.path.join(TRANSLATE_PATH(f'special://home/addons/{ADDON_ID}'), 'resources', 'lib', 'modules', 'speedtest.py')
    xbmc.executebuiltin(f'Runscript("{script_path}")')