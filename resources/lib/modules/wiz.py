import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import os
import sys
import urllib.request
import urllib.parse
import re
import time
import zipfile
from datetime import datetime

# Internal modules
from resources.lib.modules import control, maintenance

# NOTE: We are removing 'tools' import if it isn't used, 
# but checking the code, it uses 'tools._get_keyboard'.
# We need to make sure tools.py is updated next.
from resources.lib.modules import tools 
# We also need skinSwitch for the skinswap function
from resources.lib.modules import skinSwitch

# --- Constants ---
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_TITLE = "EZ Maintenance+"
DIALOG = xbmcgui.Dialog()
TRANSLATE_PATH = xbmcvfs.translatePath

# Standard Paths
HOME_PATH = TRANSLATE_PATH('special://home/')
ADDON_HOME = TRANSLATE_PATH('special://home/addons/')
USERDATA_PATH = TRANSLATE_PATH('special://home/userdata/')

# Exclusions
EXCLUDES_ADDONS = ['notification', 'packages']


def get_kodi_version():
    try:
        return float(xbmc.getInfoLabel("System.BuildVersion")[:4])
    except:
        return 0.0

def fix_special_paths():
    """
    Replaces absolute paths in XML files with special://home/ 
    to make backups portable across devices.
    """
    dp = xbmcgui.DialogProgress()
    dp.create(ADDON_TITLE, "Renaming paths...")
    
    userdata_dir = TRANSLATE_PATH('special://userdata')
    # We want to replace the resolved home path with the special variable
    home_resolved = TRANSLATE_PATH('special://home')
    
    files_processed = 0
    
    for root, dirs, files in os.walk(userdata_dir):
        for file in files:
            if file.endswith(".xml"):
                files_processed += 1
                file_path = os.path.join(root, file)
                
                dp.update(0, f"Fixing\n[COLOR dodgerblue]{file}[/COLOR]")
                
                try:
                    # Read
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Replace
                    if home_resolved in content:
                        new_content = content.replace(home_resolved, 'special://home/')
                        
                        # Write
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                except Exception:
                    pass
    
    dp.close()

def skinswap():
    current_skin = xbmc.getSkinDir()
    kodi_version = get_kodi_version()
    swapped = False

    # Switch if not already on default
    if current_skin not in ['skin.confluence', 'skin.estuary']:
        if DIALOG.yesno(ADDON_TITLE, 'Reset to default Kodi Skin (Estuary)?'):
            target_skin = 'skin.estuary' if kodi_version >= 17 else 'skin.confluence'
            
            # Call the skinSwitch module
            skinSwitch.swapSkins(target_skin)
            swapped = True
            time.sleep(1)

    # Automated handling of the confirmation dialog
    if swapped:
        # Wait for "Keep this skin?" dialog
        timeout = 0
        while not xbmc.getCondVisibility("Window.isVisible(yesnodialog)") and timeout < 10:
            time.sleep(1)
            timeout += 1

        # Interact with the dialog
        if xbmc.getCondVisibility("Window.isVisible(yesnodialog)"):
            # Move selection and confirm
            xbmc.executebuiltin("Action(Left)")
            xbmc.executebuiltin("Action(Select)")
            time.sleep(1)

    # Verify
    new_skin = xbmc.getSkinDir()
    if new_skin not in ['skin.confluence', 'skin.estuary']:
        if DIALOG.yesno(ADDON_TITLE, '[COLOR red]Auto-switch failed.[/COLOR]\nOpen Appearance Settings to switch manually?', yeslabel='Yes', nolabel='No'):
            xbmc.executebuiltin("ActivateWindow(appearancesettings)")
        else:
            return # Failure

# --- BACKUP ---

def backup(mode='full'):
    backup_path = control.setting('download.path')
    
    if not backup_path:
        control.infoDialog('Please setup a Backup Path first in Settings')
        control.openSettings(query='1.3')
        return

    if mode == 'full':
        default_name = "kodi_backup"
        source_folder = HOME_PATH
        if control.setting('BackupFixSpecialHome') == 'true':
            fix_special_paths()
    elif mode == 'userdata':
        default_name = "kodi_settings"
        source_folder = USERDATA_PATH
    else:
        return

    if os.path.exists(source_folder):
        name = tools._get_keyboard(default=default_name, heading='Name your Backup')
        if not name: 
            return

        # Sanitize name and add timestamp
        name = name.replace(' ', '_')
        timestamp = datetime.now().strftime('%Y%m%d%H%M')
        zip_name = f"{name}_{timestamp}.zip"
        zip_full_path = os.path.join(backup_path, zip_name)

        # Cleanup before backup
        try:
            maintenance.clearCache(mode='silent')
            maintenance.deleteThumbnails(mode='silent')
            maintenance.purgePackages(mode='silent')
        except: pass

        # Create Zip
        exclude_dirs = [] 
        exclude_files = ['.pyo', '.log', '.zip'] # Don't zip logs or other zips
        
        canceled = create_zip(source_folder, zip_full_path, 'Creating Backup', exclude_dirs, exclude_files)
        
        if canceled:
            if os.path.exists(zip_full_path):
                os.unlink(zip_full_path)
            DIALOG.ok(ADDON_TITLE, 'Backup Canceled')
        else:
            DIALOG.ok(ADDON_TITLE, f'Backup Complete!\nSaved to: {zip_name}')
    else:
        DIALOG.ok(ADDON_TITLE, 'Source folder not found.')

# --- RESTORE ---

def restoreFolder():
    zip_folder = control.setting('restore.path')
    if not zip_folder:
        control.infoDialog('Please setup a Restore Path first in Settings')
        control.openSettings(query='2.0')
        return

    # List Zips
    zip_files = [f for f in os.listdir(zip_folder) if f.endswith(".zip")]
    
    if not zip_files:
        DIALOG.ok(ADDON_TITLE, 'No Zip files found in restore folder.')
        return

    select = DIALOG.select("Select Backup to Restore", zip_files)
    if select != -1:
        restore_file = os.path.join(zip_folder, zip_files[select])
        restore(restore_file)

def restore(zip_file_path):
    if not DIALOG.yesno(ADDON_TITLE, 'Restore this backup?\n[COLOR red]This will overwrite your current setup![/COLOR]', yeslabel='Yes', nolabel='No'):
        return

    dp = xbmcgui.DialogProgress()
    dp.create("Restoring", "Initializing...")
    
    try:
        canceled = extract_zip(zip_file_path, HOME_PATH, dp)
        dp.close()

        if canceled:
            DIALOG.ok(ADDON_TITLE, 'Restore Canceled')
        else:
            DIALOG.ok(ADDON_TITLE, 'Restore Complete.\nKodi will now close.')
            xbmc.executebuiltin('ShutDown') # Works on most OS (Android/Windows)
            xbmc.executebuiltin('Quit')     # Fallback
    except Exception as e:
        DIALOG.ok(ADDON_TITLE, f"Restore Failed:\n{str(e)}")


# --- ZIP HELPERS ---

def create_zip(folder_path, zip_filename, message_header, exclude_dirs, exclude_files):
    abs_src = os.path.abspath(folder_path)
    
    dp = xbmcgui.DialogProgress()
    dp.create(message_header, "Scanning files...")
    
    # 1. Count files for progress bar
    total_files = 0
    file_list = []
    
    for root, dirs, files in os.walk(folder_path):
        # Filter Excludes in-place
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        files = [f for f in files if f not in exclude_files]
        
        for f in files:
            total_files += 1
            file_path = os.path.join(root, f)
            file_list.append(file_path)

    # 2. Zip It
    canceled = False
    count = 0
    
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
            for file_path in file_list:
                if dp.iscanceled():
                    canceled = True
                    break
                
                count += 1
                filename = os.path.basename(file_path)
                percent = int((count / total_files) * 100)
                
                dp.update(percent, f"Backing Up: {count}/{total_files}\n[COLOR lime]{filename}[/COLOR]")
                
                # Calculate relative path for zip structure
                arcname = file_path.replace(abs_src, "")
                zf.write(file_path, arcname)
                
    except Exception as e:
        control.infoDialog(f"Zip Error: {str(e)}", icon='ERROR')
        canceled = True

    dp.close()
    return canceled

def extract_zip(zip_file, destination, dp):
    try:
        with zipfile.ZipFile(zip_file, 'r') as zin:
            file_list = zin.infolist()
            total_files = len(file_list)
            count = 0
            
            for item in file_list:
                if dp.iscanceled():
                    return True
                
                count += 1
                percent = int((count / total_files) * 100)
                
                dp.update(percent, f"Extracting: {count}/{total_files}\n[COLOR skyblue]{item.filename}[/COLOR]")
                
                try:
                    zin.extract(item, destination)
                except Exception:
                    pass # Skip unextractable files (permissions etc)
                    
    except Exception as e:
        print(f"Extraction Error: {e}")
        return True # Treat as canceled/failed

    return False

# --- DOWNLOADER / INSTALLER ---

def buildInstaller(url):
    # Ask where to download the temp zip
    # Note: Usually wizards download to packages folder to be clean.
    # The original code asked the user. We will stick to that or default to packages.
    
    destination_dir = DIALOG.browse(0, 'Select Download Temp Folder', 'files', '', False, False)
    if not destination_dir:
        destination_dir = control.PACKAGES_PATH # Fallback to internal packages
    
    dest_file = os.path.join(destination_dir, 'custom_build.zip')
    
    # Download
    dp = xbmcgui.DialogProgress()
    dp.create(ADDON_TITLE, "Downloading Build...")
    
    success = download_file(url, dest_file, dp)
    
    if success:
        # Extract
        dp.update(0, "Extracting Build...")
        canceled = extract_zip(dest_file, HOME_PATH, dp)
        dp.close()
        
        if not canceled:
            DIALOG.ok(ADDON_TITLE, 'Installation Complete.\nKodi will now reset.')
            xbmc.executebuiltin('LoadProfile(Master user)')
    else:
        dp.close()
        DIALOG.ok(ADDON_TITLE, "Download Failed")

def download_file(url, dest_path, dp):
    start_time = time.time()
    
    try:
        # Create a custom opener to spoof User-Agent (avoid 403 Forbidden)
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0 (Kodi; EZMaintenance+)')]
        urllib.request.install_opener(opener)
        
        # Define progress hook
        def report_hook(count, block_size, total_size):
            if dp.iscanceled():
                raise Exception("Canceled")
                
            percent = int(count * block_size * 100 / total_size)
            
            # Speed Calc
            duration = time.time() - start_time
            if duration > 0:
                speed = (count * block_size) / duration / 1024 # KB/s
                speed_str = f"{speed:.2f} KB/s"
            else:
                speed_str = "..."

            dp.update(percent, f"Downloading...\nSpeed: {speed_str}")

        # Execute
        urllib.request.urlretrieve(url, dest_path, reporthook=report_hook)
        return True

    except Exception as e:
        control.infoDialog(f"Download Error: {str(e)}", icon='ERROR')
        return False