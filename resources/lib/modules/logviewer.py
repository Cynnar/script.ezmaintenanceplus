import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import os

# Import internal modules (we will check these next)
from resources.lib.modules import control
# Note: TextViewer and pastebin imports are done inside the function in the original code, 
# likely to prevent circular imports or load only when needed. I will keep that pattern.

ADDON_TITLE = "EZ Maintenance+"
ADDON_ID = 'script.ezmaintenanceplus'
DIALOG = xbmcgui.Dialog()

def logView():
    modes = ['View Log', 'Upload Log to Pastebin']
    
    # 1. Select Action
    select = control.selectDialog(modes)
    if select == -1: 
        return

    # 2. Find the Log File
    # Modern path for Kodi 19/20/21+
    log_dir = xbmcvfs.translatePath('special://logpath')
    
    # Priority list of logs to look for
    possible_logs = ['kodi.log', 'kodi.old.log']
    
    found_logs = []
    found_paths = []

    for log_name in possible_logs:
        full_path = os.path.join(log_dir, log_name)
        if xbmcvfs.exists(full_path):
            found_logs.append(log_name)
            found_paths.append(full_path)

    if not found_logs:
        DIALOG.ok(ADDON_TITLE, "No log files found in:", log_dir)
        return

    # 3. Select Log File (if multiple exist)
    if len(found_logs) > 1:
        select_log = control.selectDialog(found_logs)
        if select_log == -1: 
            return
        selected_log_path = found_paths[select_log]
    else:
        selected_log_path = found_paths[0]

    # --- ACTION: VIEW ---
    if select == 0:
        from resources.lib.modules import TextViewer
        TextViewer.text_view(selected_log_path)

    # --- ACTION: UPLOAD ---
    elif select == 1:
        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
        
        try:
            # Read file with UTF-8, ignoring errors to prevent crashes on weird symbols
            with open(selected_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                log_content = f.read()

            from resources.lib.modules import pastebin
            
            # Send to pastebin
            upload_link = pastebin.api().paste(log_content)
            
            xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
            
            if upload_link and "Error" not in upload_link:
                # Success
                qr_url = f"https://chart.googleapis.com/chart?cht=qr&chs=300x300&chl={upload_link}"
                
                # Show popup with Link
                DIALOG.ok(ADDON_TITLE, f"Log Uploaded Successfully!\nLink: [COLOR skyblue]{upload_link}[/COLOR]")
                
                # Optional: You could show a QR code here if you wanted, but text is fine.
            else:
                # Failure
                reason = upload_link if upload_link else "Unknown Error"
                DIALOG.ok(ADDON_TITLE, f"Upload Failed.\nReason: {reason}")

        except Exception as e:
            xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
            xbmc.log(f"EZ Maintenance+ Error: {str(e)}", level=xbmc.LOGERROR)
            DIALOG.ok(ADDON_TITLE, "Error reading or uploading log.")