import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import os
import shutil
import math
import time

# --- Constants ---
ADDON_ID = 'script.ezmaintenanceplus'
ADDON = xbmcaddon.Addon()
TRANSLATE_PATH = xbmcvfs.translatePath

# Standard Kodi Paths
THUMBNAIL_PATH = TRANSLATE_PATH('special://thumbnails')
CACHE_PATH = os.path.join(TRANSLATE_PATH('special://home'), 'cache')
TEMP_PATH = TRANSLATE_PATH('special://temp')
DATABASE_PATH = TRANSLATE_PATH('special://database')
PACKAGES_PATH = TRANSLATE_PATH('special://home/addons/packages')

# Assets
ICON_PATH = TRANSLATE_PATH(os.path.join('special://home/addons/' + ADDON_ID, 'icon.png'))

# Files/Folders that should NEVER be deleted during cache clean
EXCLUDE_FILES = ['xbmc.log', 'xbmc.old.log', 'kodi.log', 'kodi.old.log', 'commoncache.db', 'commoncache.socket']
EXCLUDE_DIRS = ['temp', 'archive_cache']

def _clean_directory(folder_path):
    """Helper function to clean a specific directory with exclusions."""
    if not os.path.exists(folder_path):
        return

    for root, dirs, files in os.walk(folder_path):
        # Remove excluded directories from the traversal to prevent recursion into them
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for f in files:
            if f in EXCLUDE_FILES:
                continue
            try:
                os.unlink(os.path.join(root, f))
            except Exception:
                pass # File might be locked by system
        
        for d in dirs:
            try:
                shutil.rmtree(os.path.join(root, d))
            except Exception:
                pass

def clearCache(mode='verbose'):
    # Clean Cache Folder
    _clean_directory(CACHE_PATH)
    
    # Clean Temp Folder
    _clean_directory(TEMP_PATH)

    if mode == 'verbose':
        xbmc.executebuiltin(f'Notification(Maintenance, Cache Cleared, 3000, {ICON_PATH})')

def deleteThumbnails(mode='verbose'):
    """Deletes Thumbnails and the Textures13.db database to reset image cache."""
    
    # 1. Delete the actual image files
    if os.path.exists(THUMBNAIL_PATH):
        for root, dirs, files in os.walk(THUMBNAIL_PATH):
            for f in files:
                try:
                    os.unlink(os.path.join(root, f))
                except Exception:
                    pass
            for d in dirs:
                try:
                    shutil.rmtree(os.path.join(root, d))
                except Exception:
                    pass

    # 2. Delete the database (Critical: otherwise Kodi looks for images that don't exist)
    try:
        texture_db = os.path.join(DATABASE_PATH, "Textures13.db")
        if os.path.exists(texture_db):
            os.unlink(texture_db)
    except Exception:
        pass

    if mode == 'verbose':
        xbmc.executebuiltin(f'Notification(Maintenance, Thumbnails Cleared. Restart Kodi!, 5000, {ICON_PATH})')

def purgePackages(mode='verbose'):
    if os.path.exists(PACKAGES_PATH):
        for root, dirs, files in os.walk(PACKAGES_PATH):
            for f in files:
                try:
                    os.unlink(os.path.join(root, f))
                except Exception:
                    pass
            for d in dirs:
                try:
                    shutil.rmtree(os.path.join(root, d))
                except Exception:
                    pass

    if mode == 'verbose':
        xbmc.executebuiltin(f'Notification(Maintenance, Packages Cleared, 3000, {ICON_PATH})')

def determineNextMaintenance():
    autoCleanDays = ADDON.getSetting('autoCleanDays')
    days = int(autoCleanDays) if autoCleanDays else 0

    if days > 0:
        autoCleanHour = ADDON.getSetting('autoCleanHour')
        hour = int(autoCleanHour) if autoCleanHour else 0

        t0 = int(math.floor(time.time()))
        # Add days in seconds
        t1 = t0 + (days * 24 * 3600)

        # Adjust for the specific hour of the day
        future_struct = time.localtime(t1)
        
        # Calculate offset to align with the target hour
        # (This logic preserves the original intent of aligning to a specific hour)
        t1 += (hour - future_struct.tm_hour) * 3600 - future_struct.tm_min * 60 - future_struct.tm_sec
        
        # Ensure we are strictly in the future
        while t1 <= t0:
            t1 += 24 * 3600

        # Store property on the Home window so the Service can read it
        win = xbmcgui.Window(10000)
        win.setProperty("ezmaintenance.nextMaintenanceTime", str(t1))
        
        logMaintenance(f"Next maintenance scheduled for timestamp: {t1}")

def getNextMaintenance():
    win = xbmcgui.Window(10000)
    prop = win.getProperty("ezmaintenance.nextMaintenanceTime")
    
    if not prop:
        return 0
        
    try:
        return int(prop)
    except ValueError:
        return 0

def logMaintenance(message):
    # Only log if Debug logging is enabled in Kodi to prevent spam
    xbmc.log(f"ezmaintenanceplus: {message}", level=xbmc.LOGDEBUG)