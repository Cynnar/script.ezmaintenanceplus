import requests
import base64
import urllib.parse

class api:
    def __init__(self):
        self.base_link = 'https://pastebin.com'
        self.paste_link = '/api/api_post.php'
        # Decode the API Key (Result is bytes, we decode to string for consistency)
        self.apiKey = base64.b64decode('MjNkNTNhMGMyMTdlZWY2OGM5ZWE3NDY0NDIwZTMzNmU=').decode('utf-8')

    def paste(self, text):
        url = urllib.parse.urljoin(self.base_link, self.paste_link)
        
        # Ensure text is a string
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='ignore')

        payload = {
            'api_dev_key': self.apiKey,
            'api_option': 'paste',
            'api_paste_code': text,
            'api_paste_private': '1',       # 0=Public, 1=Unlisted, 2=Private
            'api_paste_name': 'Kodi Log (EZ Maintenance+)',
            'api_paste_expire_date': '1W'   # Expire in 1 Week
        }
        
        try:
            # increased timeout to 15s for slow connections
            response = requests.post(url, data=payload, timeout=15)
            result = response.text
            
            # The Pastebin API returns the URL string if successful.
            # Otherwise it returns an error string.
            if self.base_link in result: 
                return result
            else: 
                return f"Error: {result}"
                
        except requests.exceptions.RequestException as e:
            return f"Error: Connection Failed ({str(e)})"