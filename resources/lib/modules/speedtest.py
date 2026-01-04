#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import math
import timeit
import threading
import queue
import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
import urllib.error

# Kodi Imports
import xbmc
import xbmcgui
import xbmcaddon

# --- Constants ---
__version__ = '2.1.4-Kodi'
USER_AGENT = f'Mozilla/5.0 (Kodi; EZMaintenance+/{__version__})'
DEBUG = False

# Global UI State
dp = None 
current_progress = 0  # FIX: Track progress manually since we can't read it from dp
download_str = "0.00 MB/s"

# --- Exceptions ---
class SpeedtestException(Exception): pass
class SpeedtestHTTPError(SpeedtestException): pass
class ConfigRetrievalError(SpeedtestException): pass
class ServersRetrievalError(SpeedtestException): pass
class InvalidServerIDType(SpeedtestException): pass
class NoMatchedServers(SpeedtestException): pass
class SpeedtestBestServerFailure(SpeedtestException): pass

# --- Networking Helpers ---

def build_request(url, data=None, headers=None):
    if not headers:
        headers = {}
    
    headers['User-Agent'] = USER_AGENT
    headers['Cache-Control'] = 'no-cache'
    
    # Add timestamp to bust cache
    sep = '&' if '?' in url else '?'
    final_url = f"{url}{sep}x={int(timeit.default_timer() * 1000)}"
    
    return urllib.request.Request(final_url, data=data, headers=headers)

def catch_request(request):
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.read(), response.getcode()
    except urllib.error.HTTPError as e:
        return None, e.code
    except Exception as e:
        return None, str(e)

def distance(origin, destination):
    """Calculate distance between two lat/lon tuples in km"""
    lat1, lon1 = origin
    lat2, lon2 = destination
    radius = 6371  # km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) * math.sin(dlon / 2) *
         math.sin(dlon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c

# --- Threading Classes ---

class FileGetter(threading.Thread):
    def __init__(self, url, start_time):
        self.url = url
        self.result = None
        self.start_time = start_time
        threading.Thread.__init__(self)

    def run(self):
        try:
            req = build_request(self.url)
            with urllib.request.urlopen(req, timeout=10) as f:
                self.result = len(f.read())
        except Exception:
            self.result = 0

class FilePutter(threading.Thread):
    def __init__(self, url, start_time, size):
        self.url = url
        self.start_time = start_time
        self.size = size
        self.result = None
        threading.Thread.__init__(self)

    def run(self):
        try:
            # Generate random data
            data = os.urandom(self.size)
            req = build_request(self.url, data=data)
            with urllib.request.urlopen(req, timeout=10) as f:
                f.read(11)
                self.result = self.size
        except Exception:
            self.result = 0

# --- Core Logic ---

class Speedtest(object):
    def __init__(self):
        self.config = {}
        self.servers = {}
        self.closest = []
        self.best = {}
        self.results = {'download': 0, 'upload': 0, 'ping': 0, 'share': None}

    def get_config(self):
        update_status("Retrieving Configuration...", 5)
        url = 'http://www.speedtest.net/speedtest-config.php'
        data, code = catch_request(build_request(url))
        
        if code != 200:
            raise ConfigRetrievalError("Could not retrieve config")

        try:
            root = ET.fromstring(data)
            server_config = root.find('server-config').attrib
            client = root.find('client').attrib
            
            ignore_servers = list(map(int, server_config.get('ignoreids', '').split(','))) if server_config.get('ignoreids') else []
            
            self.config = {
                'client': client,
                'ignore_servers': ignore_servers,
                'sizes': {
                    'upload': [262144, 524288, 1048576], 
                    'download': [350, 500, 750, 1000, 1500, 2000]
                },
                'threads': {
                    'upload': 8,
                    'download': 8
                },
                'upload_max': 10
            }
            
            self.lat_lon = (float(client['lat']), float(client['lon']))
        except Exception as e:
            raise SpeedtestException(f"Config parse error: {e}")

    def get_servers(self):
        update_status("Finding Servers...", 10)
        urls = [
            'http://www.speedtest.net/speedtest-servers-static.php',
            'http://c.speedtest.net/speedtest-servers-static.php',
        ]
        
        for url in urls:
            data, code = catch_request(build_request(url))
            if code == 200:
                try:
                    root = ET.fromstring(data)
                    servers = root.find('servers')
                    if servers is None: servers = root
                    
                    for server in servers.iter('server'):
                        attrib = server.attrib
                        if int(attrib.get('id')) in self.config['ignore_servers']:
                            continue
                            
                        d = distance(self.lat_lon, (float(attrib.get('lat')), float(attrib.get('lon'))))
                        attrib['d'] = d
                        
                        if d not in self.servers:
                            self.servers[d] = []
                        self.servers[d].append(attrib)
                    return
                except Exception:
                    continue
                    
        raise ServersRetrievalError("Could not retrieve server list")

    def get_best_server(self):
        update_status("Selecting Best Server...", 15)
        
        # Get 5 closest servers
        closest_keys = sorted(self.servers.keys())[:5]
        closest_servers = []
        for key in closest_keys:
            closest_servers.extend(self.servers[key])
            
        # Ping them
        results = {}
        for server in closest_servers:
            cum = []
            url_base = os.path.dirname(server['url'])
            
            # Simple latency test
            for i in range(3):
                url = f'{url_base}/latency.txt?x={i}'
                start = timeit.default_timer()
                try:
                    urllib.request.urlopen(url, timeout=2)
                    total = timeit.default_timer() - start
                    cum.append(total)
                except:
                    cum.append(10) # Heavy penalty for failure
            
            avg = sum(cum) / len(cum)
            results[avg] = server
            
        try:
            fastest = sorted(results.keys())[0]
            best = results[fastest]
            best['latency'] = fastest * 1000 # to ms
            self.best = best
            self.results['ping'] = best['latency']
            self.results['server'] = best
        except:
            raise SpeedtestBestServerFailure("Could not determine best server")

    def download(self):
        global download_str
        update_status(f"Testing Download... (Host: {self.best['sponsor']})", 20)
        
        urls = []
        for size in self.config['sizes']['download']:
            for _ in range(4): # thread multiplier
                base = os.path.dirname(self.best['url'])
                urls.append(f'{base}/random{size}x{size}.jpg')
        
        start_time = timeit.default_timer()
        
        def producer(q, urls):
            for url in urls:
                thread = FileGetter(url, start_time)
                thread.start()
                q.put(thread, True)

        finished = []
        def consumer(q, total_urls):
            while len(finished) < total_urls:
                thread = q.get(True)
                while thread.is_alive():
                    thread.join(timeout=0.1)
                if thread.result:
                    finished.append(thread.result)
                    
                    # Live Update
                    current_time = timeit.default_timer() - start_time
                    if current_time > 0:
                        speed = (sum(finished) / current_time) * 8 / 1000 / 1000
                        download_str = f"{speed:.2f} Mbps"
                        # Scale download progress from 20% to 60%
                        percent = 20 + int((len(finished)/total_urls)*40)
                        update_status(f"Download: {download_str}", percent)

        q = queue.Queue(self.config['threads']['download'])
        prod = threading.Thread(target=producer, args=(q, urls))
        cons = threading.Thread(target=consumer, args=(q, len(urls)))
        
        prod.start()
        cons.start()
        prod.join()
        cons.join()
        
        stop_time = timeit.default_timer()
        total_bytes = sum(finished)
        self.results['download'] = (total_bytes / (stop_time - start_time)) * 8

    def upload(self):
        update_status(f"Testing Upload... (DL: {download_str})", 60)
        
        sizes = []
        for size in self.config['sizes']['upload']:
            for _ in range(4):
                sizes.append(size)
                
        start_time = timeit.default_timer()
        
        def producer(q, sizes):
            for size in sizes:
                thread = FilePutter(self.best['url'], start_time, size)
                thread.start()
                q.put(thread, True)

        finished = []
        def consumer(q, total_reqs):
            while len(finished) < total_reqs:
                thread = q.get(True)
                while thread.is_alive():
                    thread.join(timeout=0.1)
                if thread.result:
                    finished.append(thread.result)
                    
                    # Live Update
                    current_time = timeit.default_timer() - start_time
                    if current_time > 0:
                        speed = (sum(finished) / current_time) * 8 / 1000 / 1000
                        # Scale upload progress from 60% to 100%
                        percent = 60 + int((len(finished)/total_reqs)*40)
                        update_status(f"Download: {download_str}\nUpload: {speed:.2f} Mbps", percent)

        q = queue.Queue(self.config['threads']['upload'])
        prod = threading.Thread(target=producer, args=(q, sizes))
        cons = threading.Thread(target=consumer, args=(q, len(sizes)))
        
        prod.start()
        cons.start()
        prod.join()
        cons.join()
        
        stop_time = timeit.default_timer()
        total_bytes = sum(finished)
        self.results['upload'] = (total_bytes / (stop_time - start_time)) * 8

    def share(self):
        update_status("Generating Result Image...", 100)
        # Construct API payload for speedtest.net to get the image
        d_speed = int(round(self.results['download'] / 1000))
        u_speed = int(round(self.results['upload'] / 1000))
        ping = int(round(self.results['ping']))
        
        api_data = {
            'recommendedserverid': self.best['id'],
            'ping': ping,
            'download': d_speed,
            'upload': u_speed,
            'bytesreceived': 0,
            'bytessent': 0,
            'serverid': self.best['id']
        }
        
        req_data = urllib.parse.urlencode(api_data).encode()
        headers = {'Referer': 'http://c.speedtest.net/flash/speedtest.swf'}
        req = urllib.request.Request('http://www.speedtest.net/api/api.php', data=req_data, headers=headers)
        
        try:
            data, code = catch_request(req)
            if code == 200:
                qs = urllib.parse.parse_qs(data.decode())
                if 'resultid' in qs:
                    rid = qs['resultid'][0]
                    self.results['share'] = f'http://www.speedtest.net/result/{rid}.png'
        except:
            pass
            
        return self.results['share']

# --- UI Helpers ---

def update_status(msg, percent=None):
    global current_progress
    
    if dp.iscanceled():
        raise SpeedtestException("User Canceled")
    
    # Update the tracking variable if a new percent is provided
    if percent is not None:
        current_progress = percent
        
    dp.update(current_progress, f"Speedtest.net\n{msg}")

class ResultWindow(xbmcgui.WindowDialog):
    def __init__(self, image_url):
        super().__init__()
        # Create a centered image
        # Assuming 1080p layout approx.
        width = 800
        height = 450
        x = (1920 - width) // 2
        y = (1080 - height) // 2
        
        self.img = xbmcgui.ControlImage(x, y, width, height, image_url)
        self.addControl(self.img)
        
        # Add a text hint
        self.lbl = xbmcgui.ControlLabel(x, y + height + 10, width, 50, "Press [Back] or wait 10s to close", alignment=2)
        self.addControl(self.lbl)

# --- Main Execution ---

def run_test():
    global dp
    dp = xbmcgui.DialogProgress()
    dp.create('Speedtest', 'Initializing...')
    
    st = Speedtest()
    
    try:
        st.get_config()
        st.get_servers()
        st.get_best_server()
        
        st.download()
        st.upload()
        
        img_url = st.share()
        
        dp.close()
        
        # Display Results
        d_mbps = st.results['download'] / 1000 / 1000
        u_mbps = st.results['upload'] / 1000 / 1000
        p_ms = st.results['ping']
        
        if img_url:
            win = ResultWindow(img_url)
            win.show()
            # Wait loop to allow user to close
            for _ in range(100): # 10 seconds
                if xbmc.getCondVisibility('Window.IsActive(dialog)'): # if user creates another dialog
                    break
                xbmc.sleep(100)
            win.close()
            del win
        else:
            xbmcgui.Dialog().ok("Speedtest Results", 
                                f"Ping: {p_ms:.0f} ms\n"
                                f"Down: {d_mbps:.2f} Mbps\n"
                                f"Up:   {u_mbps:.2f} Mbps")

    except Exception as e:
        dp.close()
        xbmcgui.Dialog().ok("Speedtest Error", str(e))

if __name__ == '__main__':
    run_test()