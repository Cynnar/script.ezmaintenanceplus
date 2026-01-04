import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import os
import re
from math import trunc

# --- Constants ---
ADDON = xbmcaddon.Addon()
ADDON_TITLE = "EZ Maintenance+"
DIALOG = xbmcgui.Dialog()
TRANSLATE_PATH = xbmcvfs.translatePath
XML_FILE = TRANSLATE_PATH('special://home/userdata/advancedsettings.xml')

def get_xml_template(memory_size):
    """Returns modern advancedsettings.xml structure for Kodi 17+"""
    return f"""<advancedsettings>
  <network>
    <curlclienttimeout>10</curlclienttimeout>
    <curllowspeedtime>20</curllowspeedtime>
    <curlretries>2</curlretries>
  </network>
  <cache>
    <memorysize>{memory_size}</memorysize>
    <buffermode>2</buffermode>
    <readfactor>20</readfactor>
  </cache>
</advancedsettings>"""

def advancedSettings():
    # 1. Calculate Optimal Buffer Size
    # Get Free Memory string (e.g., "2048MB")
    free_mem_str = xbmc.getInfoLabel("System.FreeMemory")
    
    # Extract digits
    clean_mem = re.sub('[^0-9]', '', free_mem_str)
    
    if not clean_mem:
        DIALOG.ok(ADDON_TITLE, "Could not detect system memory.\nPlease set buffer size manually.")
        optimal_mb = 0
        optimal_bytes = 0
    else:
        free_mem_mb = int(clean_mem)
        # Rule of thumb: Use 1/3 of Free RAM for buffer
        optimal_mb = round(free_mem_mb / 3)
        optimal_bytes = trunc(optimal_mb * 1024 * 1024)

    # 2. Ask User
    msg = (f"Based on your free Memory ({free_mem_mb} MB),\n"
           f"your optimal buffer size is: {optimal_mb} MB ({optimal_bytes} Bytes)\n\n"
           "This will overwrite your current advancedsettings.xml!")
    
    choice = DIALOG.yesno(ADDON_TITLE, msg, yeslabel='Use Optimal', nolabel='Enter Manually')

    final_bytes = None

    if choice == 1: # Use Optimal
        final_bytes = str(optimal_bytes)
        
    else: # Manual Input
        user_input = _get_keyboard(default=str(optimal_bytes), heading="Enter Buffer Size in Bytes")
        if user_input:
            if user_input.isdigit():
                final_bytes = user_input
            else:
                DIALOG.ok(ADDON_TITLE, "Invalid input. Please enter a number.")
                return

    # 3. Write File
    if final_bytes:
        try:
            xml_content = get_xml_template(final_bytes)
            
            with open(XML_FILE, "w", encoding='utf-8') as f:
                f.write(xml_content)
                
            DIALOG.ok(ADDON_TITLE, f"Buffer Size Set to: {final_bytes} Bytes\nRestart Kodi to apply.")
            
        except Exception as e:
            DIALOG.ok(ADDON_TITLE, f"Error writing file:\n{str(e)}")

def _get_keyboard(default="", heading="", hidden=False):
    """Shows a keyboard and returns the value."""
    keyboard = xbmc.Keyboard(default, heading, hidden)
    keyboard.doModal()
    
    if keyboard.isConfirmed():
        return keyboard.getText()
    return None