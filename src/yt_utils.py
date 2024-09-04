import yt_dlp
from yt_dlp.utils import download_range_func
import time

allowed_resolutions = ['2160', '1440', '1080', '720', '480', '360', '240', '144']

def download_yt_dlp(url, ydl_opts, start, end, sign, length, base_time):
    if abs(end-start) < length:
        ydl_opts['download_ranges'] = download_range_func(None, [(base_time+(sign*start), base_time+(sign*end))])
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info['requested_downloads'][0]['filepath'], info['resolution'], info['abr']
    
def get_yt_video_info(url, proxy_str, config):
    ydl_opts = {'proxy': proxy_str,
                'quiet': True,
                'cookiefile': config['cookiefile'],
                'source_address': config['ip_address']
                }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        is_live = info['is_live']
        if is_live:
            base_time = time.time()
            duration = base_time - info['release_timestamp']
        else:
            base_time = 0
            duration = info['duration']
        
        return info['title'], is_live, duration, base_time