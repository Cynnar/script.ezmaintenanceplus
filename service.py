import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import os
import time
from resources.lib.modules import maintenance

# --- Constants & Setup ---
ADDON_ID = 'script.ezmaintenanceplus'
ADDON = xbmcaddon.Addon()
# Modern path translation for Kodi 19+
TRANSLATE_PATH = xbmcvfs.translatePath
PACKAGES_DIR = TRANSLATE_PATH(os.path.join('special://home/addons/packages', ''))
THUMBNAILS_DIR = TRANSLATE_PATH('special://home/userdata/Thumbnails')
ICON_PATH = TRANSLATE_PATH(os.path.join('special://home/addons/' + ADDON_ID, 'icon.png'))

def get_setting(setting_id):
    return ADDON.getSetting(setting_id)

def get_folder_size(start_path):
    total_size = 0
    file_count = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            file_count += 1
            fp = os.path.join(dirpath, f)
            # Skip if broken link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size, file_count

def check_startup_maintenance():
    """Performs the heavy file system checks once at startup."""
    
    # Settings
    notify_mode = get_setting('notify_mode')
    auto_clean_cache = get_setting('startup.cache')
    filesize_alert_mb = int(get_setting('filesize_alert'))
    thumbsize_alert_mb = int(get_setting('filesizethumb_alert'))
    
    # 1. Check Packages Folder
    pkg_size_bytes, pkg_count = get_folder_size(PACKAGES_DIR)
    pkg_size_mb = pkg_size_bytes / 1024000.0
    
    if pkg_size_mb > filesize_alert_mb:
        msg = (f"[COLOR=red]Autocleaner[/COLOR]\n"
               f"The packages folder is [COLOR red]{pkg_size_mb:.0f} MB[/COLOR] - "
               f"[COLOR red]{pkg_count}[/COLOR] zip files\n"
               f"Do you want to clean it now?")
        
        if xbmcgui.Dialog().yesno("EZ Maintenance+", msg, yeslabel='Yes', nolabel='No'):
            maintenance.purgePackages()

    # 2. Check Thumbnails Folder
    thumb_size_bytes, _ = get_folder_size(THUMBNAILS_DIR)
    thumb_size_mb = thumb_size_bytes / 1024000.0

    if thumb_size_mb > thumbsize_alert_mb:
        msg = (f"[COLOR=red]Autocleaner[/COLOR]\n"
               f"The images folder is [COLOR red]{thumb_size_mb:.0f} MB[/COLOR]\n"
               f"Do you want to clean it now?")
        
        if xbmcgui.Dialog().yesno("EZ Maintenance+", msg, yeslabel='Yes', nolabel='No'):
            maintenance.deleteThumbnails()

    # 3. Notification
    if notify_mode == 'true':
        msg = f"Packages: {pkg_size_mb:.0f} MB - Images: {thumb_size_mb:.0f} MB"
        xbmc.executebuiltin(f'Notification(Maintenance Status, {msg}, 5000, {ICON_PATH})')

    # 4. Auto Clean Cache (if enabled)
    if auto_clean_cache == 'true':
        maintenance.clearCache()

    maintenance.logMaintenance("Service startup checks complete")


class MaintenanceMonitor(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        maintenance.logMaintenance("Monitor initialized")
        maintenance.determineNextMaintenance()

    def onSettingsChanged(self):
        maintenance.logMaintenance("Settings changed, updating schedule")
        maintenance.determineNextMaintenance()


if __name__ == '__main__':
    monitor = MaintenanceMonitor()

    # EFFICIENCY FIX: Wait 10 seconds before doing heavy IO checks.
    # This prevents the addon from slowing down the Kodi boot process.
    if not monitor.waitForAbort(10):
        
        # Run the startup checks (Packages/Thumbnails)
        check_startup_maintenance()

        # Main Service Loop
        while not monitor.abortRequested():
            
            # EFFICIENCY FIX: Increased wait time from 10s to 60s.
            # Maintenance does not need to be checked every 10 seconds.
            if monitor.waitForAbort(60):
                break

            if not xbmc.Player().isPlayingVideo():
                next_maintenance = maintenance.getNextMaintenance()
                
                # Check if it's time to run scheduled maintenance
                if next_maintenance > 0 and time.time() >= next_maintenance:
                    xbmc.log("ezmaintenanceplus: Scheduled AutoClean started", level=xbmc.LOGINFO)
                    maintenance.clearCache()
                    xbmc.log("ezmaintenanceplus: Scheduled AutoClean done", level=xbmc.LOGINFO)
                    
                    # Reset the timer
                    maintenance.determineNextMaintenance()