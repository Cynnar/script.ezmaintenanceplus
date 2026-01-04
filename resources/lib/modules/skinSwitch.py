import xbmc
import json

def get_setting(setting_id):
    """Retrieves a setting value via JSONRPC"""
    try:
        # Construct the payload
        # Note: In newer Kodi versions (19+), Settings.GetSettingValue is correct.
        query = {
            "jsonrpc": "2.0", 
            "method": "Settings.GetSettingValue", 
            "params": {"setting": setting_id}, 
            "id": 1
        }
        
        response_str = xbmc.executeJSONRPC(json.dumps(query))
        response = json.loads(response_str)
        
        # Python 3 check (has_key is dead)
        if 'result' in response:
            if 'value' in response['result']:
                return response['result']['value']
                
    except Exception as e:
        xbmc.log(f"skinSwitch Error (Get): {str(e)}", level=xbmc.LOGERROR)
        pass
        
    return None

def set_setting(setting_id, value):
    """Sets a setting value via JSONRPC"""
    try:
        query = {
            "jsonrpc": "2.0", 
            "method": "Settings.SetSettingValue", 
            "params": {"setting": setting_id, "value": value}, 
            "id": 1
        }
        
        xbmc.executeJSONRPC(json.dumps(query))
        
    except Exception as e:
        xbmc.log(f"skinSwitch Error (Set): {str(e)}", level=xbmc.LOGERROR)
        pass

def swapSkins(skin_id):
    """Switches the Kodi skin to the specified ID (e.g., skin.estuary)"""
    setting_key = 'lookandfeel.skin'
    
    # Optional: Check current skin first to avoid redundant switch
    current_skin = get_setting(setting_key)
    
    if current_skin != skin_id:
        set_setting(setting_key, skin_id)