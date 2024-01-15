from pytube import YouTube, helpers
import ffmpeg
import os, errno
import re
import yaml
import argparse
from telethon import TelegramClient, events
import datetime
import tempfile
import http
from instagrapi import Client
from hezar.models import Model

url_pattern = "(https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z]{2,}(\.[a-zA-Z]{2,})(\.[a-zA-Z]{2,})?\/[a-zA-Z0-9]{2,}|((https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z]{2,}(\.[a-zA-Z]{2,})(\.[a-zA-Z]{2,})?)|(https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z0-9]{2,}\.[a-zA-Z0-9]{2,}\.[a-zA-Z0-9]{2,}(\.[a-zA-Z0-9]{2,})?"
youtube_url_pattern = "^((?:https?:)?//)?((?:www|m).)?((?:youtube.com|youtu.be))(/(?:[\w-]+?v=|embed/|v/|shorts/)?)([\w-]+)(\S+)?.*"
instagram_url_pattern = "((?:https?:\/\/)?(?:www\.)?instagram\.com\/(?:p|reel)\/([^/?#&]+)).*"
allowed_resolutions = ['2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p']

parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.yaml')
args = parser.parse_args()

config = {}
with open(args.config) as f:
    config = yaml.load(f, Loader=yaml.loader.SafeLoader)

allowed_youtube_user_ids = config['allowed_youtube_user_ids']
allowed_youtube_chat_ids = config['allowed_youtube_chat_ids']
allowed_insta_user_ids = config['allowed_insta_user_ids']
allowed_insta_chat_ids = config['allowed_insta_chat_ids']
allowed_stt_chat_ids = config['allowed_stt_chat_ids']

insta = Client()
print("loading model...")
model = Model.load("hezarai/whisper-small-fa")
print("model loaded successfully...")

proxy = None
if config['proxy']:
    proxy_str = f"{config['proxy']['proxy_type']}://{config['proxy']['addr']}:{config['proxy']['port']}"
    proxies = {"http": proxy_str,
               "https": proxy_str}
    helpers.install_proxy(proxies)
    proxy = config['proxy']
    insta.set_proxy(proxy_str)
    
client = TelegramClient(config['session'], config['api_id'], config['api_hash'], proxy=proxy).start(phone=config['phone_number'])
insta.login_by_sessionid(config['instagram_session_id'])

@client.on(events.NewMessage(func=lambda e: (e.is_private or e.chat_id in allowed_stt_chat_ids) and e.message.voice))
async def handler_insta(event):
    try:
        with tempfile.TemporaryDirectory() as tempdir:
            file_name = os.path.join(tempdir, f"{event.id}.mp3")
            await event.message.download_media(file=file_name)
            transcripts = model.predict(file_name)
            transcripts = transcripts[0]['text']
            await event.reply(f"#Bot #STT\n{transcripts}")
    except Exception as e:
        print(e)
        print("failed to convert speech to text.")

@client.on(events.NewMessage(func=lambda e: e.chat_id in allowed_insta_chat_ids or e.sender_id in allowed_insta_user_ids, pattern=instagram_url_pattern))
async def handler_insta(event):
    text = event.raw_text
    url = parse_args_insta(text)
    if url is not None:
        await download_insta(event, url)
    else:
        print("invalid input.")

async def download_insta(event, url):
    msg = "#Bot: Downloading..."
    message = await event.reply(msg)
    print(msg)
    try:
        media_pk = insta.media_pk_from_url(url)
        media_info = insta.media_info(media_pk)
        media_type = media_info.media_type
        product_type = media_info.product_type
        caption = media_info.caption_text
        with tempfile.TemporaryDirectory() as tempdir:
            if media_type == 1: # photo
                media_path = insta.photo_download(media_pk, tempdir)
            elif media_type == 2 and product_type == 'feed': # video
                media_path = insta.video_download(media_pk, tempdir)
            elif media_type == 2 and product_type == 'clips': # reel
                media_path = insta.clip_download(media_pk, tempdir)
            elif media_type == 2 and product_type == 'igtv': # igtv
                media_path = insta.igtv_download(media_pk, tempdir)
            elif media_type == 8: # album
                media_path = insta.album_download(media_pk, tempdir)
            else:
                await message.delete()
                msg = "#Bot: failed to download file."
                print(msg)
                await event.reply(msg)
                return
            await event.respond(f"#Bot #Instagram\n{caption}\nLink: {url}", link_preview=False, file=media_path)
            await message.delete()
            await event.message.delete()
    except Exception as e:
        print(e)
        await message.delete()
        msg = "#Bot: failed to download file."
        print(msg)
        await event.reply(msg)
        
def parse_args_insta(text):
    url = None
    try:
        splitted_message = re.split(' ', text)
        if len(splitted_message) == 0:
            return url
        elif len(splitted_message) == 1:
            return url
        elif len(splitted_message) == 2:
            if get_int(splitted_message[1]) != 1:
                return url
        else:
            return url
        url = splitted_message[0]
        return url
    except:
        return url

def get_int(string):
    try:
        return int(string)
    except ValueError:
        return None

def silentremove(filename):
    try:
        os.remove(filename)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

def combine_video_audio(video_file, audio_file, output_file):
    video_stream = ffmpeg.input(video_file)
    audio_stream = ffmpeg.input(audio_file)
    ffmpeg.output(audio_stream, video_stream, output_file, acodec='copy', vcodec='copy', loglevel=config['log_level']).run(overwrite_output=True)
  
def trim(input_path, output_path, start, end):
    input_stream = ffmpeg.input(input_path, ss=(str(datetime.timedelta(seconds=start))), to=(str(datetime.timedelta(seconds=end))))
    ffmpeg.output(input_stream, output_path, acodec='copy', vcodec='copy', loglevel=config['log_level']).run(overwrite_output=True)

def parse_args_yt(text):
    resolution = None
    start = None
    end = None
    url = None
    try:
        splitted_message = re.split(' ', text)
        if len(splitted_message) == 0:
            return url, resolution, start, end
        elif len(splitted_message) == 1:
            return url, resolution, start, end
        elif len(splitted_message) == 2:
            if splitted_message[1] in allowed_resolutions:
                resolution = splitted_message[1]
            elif get_int(splitted_message[1]) != 1:
                return url, resolution, start, end
        elif len(splitted_message) == 3:
            start = get_int(splitted_message[1])
            end = get_int(splitted_message[2])
            if start is None or end is None:
                return url, resolution, start, end
        elif len(splitted_message) == 4:
            if splitted_message[1] in allowed_resolutions:
                resolution = splitted_message[1]
            start = get_int(splitted_message[2])
            end = get_int(splitted_message[3])
            if resolution is None or start is None or end is None:
                return url, resolution, start, end
        else:
            return url, resolution, start, end
        if start is not None:
            if start >= end or start < 0 or end < 0:
                return url, resolution, start, end
        url = splitted_message[0]
        return url, resolution, start, end
    except:
        return url, resolution, start, end
    
@client.on(events.NewMessage(func=lambda e: e.chat_id in allowed_youtube_chat_ids or e.sender_id in allowed_youtube_user_ids, pattern=youtube_url_pattern))
async def handler_yt(event):
    text = event.raw_text
    url, resolution, start, end = parse_args_yt(text)
    if url is not None:
        await download_youtube(event, url, resolution, start, end)
    else:
        print("invalid input.")

async def download_youtube(event, url, resolution=None, start=None, end=None):
    msg = "#Bot: Downloading ....."
    print(msg)
    message = await event.reply(msg)
    try:
        resolutions = config['default_resolution_order']
        yt = YouTube(url)
        if yt.length > config['max_video_length']:
            await message.delete()
            msg = f"#Bot: video is longer than {config['max_video_length']} seconds."
            print(msg)
            await event.reply(msg)
            return
        video_title = yt.title
        print(f"Downloading {video_title} ...")
        streams = yt.streams
        stream = None
        video = None
        audio = None
        audio = streams.get_audio_only()
        if resolution is not None:
            if len(streams.filter(res=resolution, progressive=True)):
                stream = streams.filter(res=resolution, progressive=True).first()
            if stream is None:
                if len(streams.filter(res=resolution, only_video=True)):
                    video = streams.filter(res=resolution, only_video=True).first()
        if stream is None and video is None:
            for res in resolutions:
                if len(streams.filter(res=res, progressive=True)):
                    stream = streams.filter(res=res, progressive=True).first()
                    break
                if len(streams.filter(res=res, only_video=True)):
                    video = streams.filter(res=res, only_video=True).first()
                    break
        if stream is None and video is None:
            stream = streams.filter(progressive=True).get_highest_resolution()
        if stream is None and video is None:
            video = streams.filter(only_video=True).get_highest_resolution()
        if stream is None and video is None:
            await message.delete()
            msg ="#Bot: no video stream found."
            await event.reply(msg)
            print(msg)
            return
        elif stream is None and audio is None:
            await message.delete()
            msg = "#Bot: no audio stream found."
            await event.reply(msg)
            print(msg)
            return
        combined_name = None
        audio_name = None
        with tempfile.TemporaryDirectory() as tempdir:
            if stream:
                video_name = stream.download(output_path=tempdir, max_retries=10)
                print(f"{video_title} downloaded successfully")
                file_name = os.path.splitext(video_name)[0]
                file_extention = os.path.splitext(video_name)[-1]
                if start is not None and end is not None:
                    output_name = f'{file_name}_out{file_extention}'
                    trim(video_name, output_name, start=start, end=end)
                else:
                    output_name = video_name
            else:
                video_default_name = video.download(output_path=tempdir, max_retries=10)
                file_name = os.path.splitext(video_default_name)[0]
                file_extention = os.path.splitext(video_default_name)[-1]
                video_name = f"{file_name}_video{file_extention}"
                os.rename(video_default_name, video_name)
                audio_name = audio.download(output_path=tempdir, max_retries=10)
                print(f"{video_title} downloaded successfully")
                combined_name = f'{file_name}_combined{file_extention}'
                combine_video_audio(video_name, audio_name, combined_name)
                if start is not None and end is not None:
                    output_name = f'{file_name}_out{file_extention}'
                    trim(combined_name, output_name, start=start, end=end)
                else:
                    output_name = combined_name
            msg = f"#Bot #Youtube\n{video_title}\nLink: {url}"
            if start is not None:
                msg += f"\nStart: {datetime.timedelta(seconds=start)} ({start}s), End: {datetime.timedelta(seconds=end)} ({end}s)"
            if stream:
                msg += f"\nResolution: {stream.resolution}"
            else:
                msg += f"\nResolution: {video.resolution}"
            await event.respond(msg, link_preview=False, file=output_name)
            await message.delete()
            await event.message.delete()
    except (http.client.IncompleteRead) as e:
        print(e)
        await message.delete()
        await download_youtube(event, url, resolution, start, end)
    except Exception as e:
        print(e)
        await message.delete()
        msg = "#Bot: failed to download video."
        await event.reply(msg)
        print(msg)

if __name__ == '__main__':
    client.run_until_disconnected()
