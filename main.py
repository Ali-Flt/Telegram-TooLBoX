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


def get_int(string=None):
    if string is None:
        return None
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

def convet_to_mp3(audio_file):
    audio_stream = ffmpeg.input(audio_file)
    file_name = os.path.splitext(audio_file)[0]
    output_file = f"{file_name}_mp3.mp3"
    ffmpeg.output(audio_stream, output_file, vn=None, loglevel=config['log_level']).run(overwrite_output=True)
    return output_file
    
def remove_audio(video_file, output_file):
    video_stream = ffmpeg.input(video_file)
    ffmpeg.output(video_stream, output_file, vcodec='copy', an=None, loglevel=config['log_level']).run(overwrite_output=True)
    
def combine_video_audio(video_file, audio_file, output_file):
    video_stream = ffmpeg.input(video_file)
    audio_stream = ffmpeg.input(audio_file)
    ffmpeg.output(audio_stream, video_stream, output_file, acodec='copy', vcodec='copy', loglevel=config['log_level']).run(overwrite_output=True)
  
def trim(input_path, output_path, start, end):
    input_stream = ffmpeg.input(input_path, ss=(str(datetime.timedelta(seconds=start))), to=(str(datetime.timedelta(seconds=end))))
    ffmpeg.output(input_stream, output_path, acodec='copy', vcodec='copy', loglevel=config['log_level']).run(overwrite_output=True)

def get_timestamp(time_str=None):
    if time_str is None:
        return None
    int_time = get_int(time_str)
    if int_time is not None:
        return int_time
    hour = 0
    try:
        timestamp = datetime.datetime.strptime(time_str, "%M:%S")
    except ValueError:
        try:
            timestamp = datetime.datetime.strptime(time_str, "%H:%M:%S")
            hour = timestamp.hour
        except ValueError:
            return None
    return hour*3600 + timestamp.minute*60 + timestamp.second
            
def get_valid_resolution(res_str=None):
    if res_str is None:
        return None
    if res_str in allowed_resolutions:
        return res_str
    return None

async def abort_and_reply(msg, msg_to_delete, event):
    await msg_to_delete.delete()
    print(msg)
    await event.reply(msg)
    
url_pattern = "(https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z]{2,}(\.[a-zA-Z]{2,})(\.[a-zA-Z]{2,})?\/[a-zA-Z0-9]{2,}|((https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z]{2,}(\.[a-zA-Z]{2,})(\.[a-zA-Z]{2,})?)|(https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z0-9]{2,}\.[a-zA-Z0-9]{2,}\.[a-zA-Z0-9]{2,}(\.[a-zA-Z0-9]{2,})?"
youtube_url_pattern = "^((?:https?:)?//)?((?:www|m).)?((?:youtube.com|youtu.be))(/(?:[\w-]+?v=|embed/|v/|shorts/)?)([\w-]+)(\S+)?.*"
instagram_url_pattern = "(?:(?:http|https):\/\/)?(?:www\.)?(?:instagram\.com|instagr\.am)\/([A-Za-z0-9-_\.]+).*"
make_gif_patter = "^gif.*"
allowed_resolutions = ['2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p']

yt_parser = argparse.ArgumentParser(add_help=False, prog='youtube_media_url', exit_on_error=False)
yt_parser.add_argument('-1', dest='enable', action='store_const', const=True, default=False, help="add this to enable the bot")
yt_parser.add_argument('-r', dest='resolution', type=str, help="video resolution (e.g. 1080p)")
yt_parser.add_argument('-s', dest='start', type=str, help="start time in seconds or MM:SS")
yt_parser.add_argument('-e', dest='end', type=str, help="end time in seconds, MM:SS")
yt_parser.add_argument('-d', dest='duration', type=str, help="duration time in seconds, MM:SS")
yt_parser.add_argument('-ao', dest='onlyaudio', action='store_const', const=True, default=False, help="get only audio stream")
yt_parser.add_argument('-vo', dest='noaudio', action='store_const', const=True, default=False, help="get only video stream")
yt_parser.add_argument('-gif', dest='gif', action='store_const', const=True, default=False, help="convert video to gif")
yt_parser.add_argument('-h', dest='help', action='store_const', const=True, default=False, help="print this help command")

insta_parser = argparse.ArgumentParser(add_help=False, prog='instagram_media_url', exit_on_error=False)
insta_parser.add_argument('-1', dest='enable', action='store_const', const=True, default=False, help="add this to enable the bot")
insta_parser.add_argument('-h', dest='help', action='store_const', const=True, default=False, help="print this help command")

gif_parser = argparse.ArgumentParser(add_help=False, prog='gif', exit_on_error=False)
gif_parser.add_argument('-1', dest='enable', action='store_const', const=True, default=False, help="add this to enable the bot")
gif_parser.add_argument('-h', dest='help', action='store_const', const=True, default=False, help="print this help command")

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
allowed_gifying_chat_ids = config['allowed_gifying_chat_ids']
allowed_gifying_user_ids = config['allowed_gifying_user_ids']
insta = Client()

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

@client.on(events.NewMessage(func=lambda e: e.chat_id in allowed_gifying_chat_ids or e.sender_id in allowed_gifying_user_ids, pattern=make_gif_patter))
async def handler_make_gif(event):
    args = parse_args_gif(event.raw_text)
    if args is None:
        return
    if args.help:
        await event.message.delete()
        await event.respond(f"`{gif_parser.format_help()}`\nDon't forget to attach the video to your message.\n__A Gif maker by @a_flt__")
        return
    if not args.enable:
        return
    if event.message.video:
        await make_gif(event)

def parse_args_gif(text):
    splitted_text = re.split(' ', text)
    if len(splitted_text) < 2:
        return None
    try:
        return gif_parser.parse_known_args(splitted_text[1:])[0]
    except Exception as e:
        print(e)
        return None
    
async def make_gif(event):
    message = "#Bot: converting to gif..."
    await event.reply(message)
    print(message)
    try:
        with tempfile.TemporaryDirectory() as tempdir:
            file_name = os.path.join(tempdir, f"{event.id}.mp4")
            await event.message.download_media(file=file_name)
            output_name = os.path.join(tempdir, f"{event.id}_noaudio.mp4")
            remove_audio(file_name, output_name)
            await event.respond(f"#Bot #gif_maker", file=output_name, nosound_video=False)
            await event.message.delete()
    except Exception as e:
        print(e)
        msg = "#Bot: failed to convert to gif."
        abort_and_reply(msg, message, event)
        
        
@client.on(events.NewMessage(func=lambda e: e.chat_id in allowed_insta_chat_ids or e.sender_id in allowed_insta_user_ids, pattern=instagram_url_pattern))
async def handler_insta(event):
    url, args = parse_args_insta(event.raw_text)
    if args is None:
        return
    if args.help:
        await event.message.delete()
        await event.respond(f"`{insta_parser.format_help()}`\n__A YT & IG downloader by @a_flt__")
        return
    if not args.enable:
        return
    if url is not None:
        await download_insta(event, url)

def parse_args_insta(text):
    splitted_text = re.split(' ', text)
    if len(splitted_text) < 2:
        return None, None
    try:
        return splitted_text[0], insta_parser.parse_known_args(splitted_text[1:])[0]
    except Exception as e:
        print(e)
        return None, None
    
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
                msg = "#Bot: failed to download file."
                await abort_and_reply(msg, message, event)
                return
            await event.respond(f"#Bot #Instagram\n{caption}\nLink: {url}", link_preview=False, file=media_path)
            await message.delete()
            await event.message.delete()
    except Exception as e:
        print(e)
        msg = "#Bot: failed to download file."
        await abort_and_reply(msg, message, event)
            
@client.on(events.NewMessage(func=lambda e: e.chat_id in allowed_youtube_chat_ids or e.sender_id in allowed_youtube_user_ids, pattern=youtube_url_pattern))
async def handler_yt(event):
    url, args = parse_args_yt(event.raw_text)
    if args is None:
        return
    if args.help:
        await event.message.delete()
        await event.respond(f"`{yt_parser.format_help()}`\n__A YT & IG downloader by @a_flt__")
        return
    if not args.enable:
        return
    if url is not None:
        await download_youtube(event, url, args)

def parse_args_yt(text):
    splitted_text = re.split(' ', text)
    if len(splitted_text) < 2:
        return None, None
    try:
        return splitted_text[0], yt_parser.parse_known_args(splitted_text[1:])[0]
    except Exception as e:
        print(e)
        return None, None
    
async def download_youtube(event, url, args):
    msg = "#Bot: Downloading ....."
    print(msg)
    message = await event.reply(msg)
    try:
        yt = YouTube(url)
        if yt.length > config['max_video_length']:
            msg = f"#Bot: video is longer than {config['max_video_length']} seconds."
            await abort_and_reply(msg, message, event)
            return
        start = get_timestamp(args.start)
        duration = get_timestamp(args.duration) 
        end = get_timestamp(args.end)
        if start is not None and duration is not None:
            end = start + duration
        elif end is not None and duration is not None:
            start = end - duration
        if start is not None:
            start = min(start, yt.length)
        else:
            start = 0
        if end is not None:
            end = min(end, yt.length)
        else:
            end = yt.length
        if start >= end:
            msg = "#Bot: timestamps out of range."
            await abort_and_reply(msg, message, event)
            return
        if start == 0 and end == yt.length:
            do_trim = False
        else:
            do_trim = True
        resolution = get_valid_resolution(args.resolution)
        video_title = yt.title
        print(f"Downloading {video_title} ...")
        streams = yt.streams
        stream = None
        video = None
        audio = streams.get_audio_only()
        resolutions = config['default_resolution_order']
        if resolution is not None:
            if len(streams.filter(res=resolution, progressive=True)):
                stream = streams.filter(res=resolution, progressive=True).first()
            if len(streams.filter(res=resolution, only_video=True)):
                video = streams.filter(res=resolution, only_video=True).first()
        if stream is None:
            for res in resolutions:
                if len(streams.filter(res=res, progressive=True)):
                    stream = streams.filter(res=res, progressive=True).first()
                    break
        if video is None:
            for res in resolutions:
                if len(streams.filter(res=res, only_video=True)):
                    video = streams.filter(res=res, only_video=True).first()
                    break
        if stream is None:
            stream = streams.filter(progressive=True).get_highest_resolution()
        if video is None:
            video = streams.filter(only_video=True).get_highest_resolution()
        if stream is None and video is None and audio is None:
            msg ="#Bot: no video stream found."
            await abort_and_reply(msg, message, event)
            return
        nosound_video = None
        msg_extra = ''
        with tempfile.TemporaryDirectory() as tempdir:
            if args.onlyaudio:
                msg_extra = '#onlyaudio'
                audio_name = audio.download(output_path=tempdir, max_retries=10)
                print(f"{video_title} downloaded successfully")
                file_extention = os.path.splitext(audio_name)[-1]
                if do_trim:
                    output_name = os.path.join(tempdir, f'{event.id}_out{file_extention}')
                    trim(audio_name, output_name, start=start, end=end)
                else:
                    output_name = audio_name
                output_name = convet_to_mp3(output_name)
            elif args.noaudio or args.gif:
                if args.noaudio:
                    nosound_video = True
                    msg_extra = '#noaudio'
                else:
                    nosound_video = False
                    msg_extra = '#gif'
                video_name = video.download(output_path=tempdir, max_retries=10)
                print(f"{video_title} downloaded successfully")
                file_extention = os.path.splitext(video_name)[-1]
                if do_trim:
                    output_name = os.path.join(tempdir, f'{event.id}_out{file_extention}')
                    trim(video_name, output_name, start=start, end=end)
                else:
                    output_name = video_name
            elif stream:
                video_name = stream.download(output_path=tempdir, max_retries=10)
                print(f"{video_title} downloaded successfully")
                file_extention = os.path.splitext(video_name)[-1]
                if do_trim:
                    output_name = os.path.join(tempdir, f'{event.id}_out{file_extention}')
                    trim(video_name, output_name, start=start, end=end)
                else:
                    output_name = video_name
            else:
                video_default_name = video.download(output_path=tempdir, max_retries=10)
                file_extention = os.path.splitext(video_default_name)[-1]
                video_name = os.path.join(tempdir, f"{event.id}_video{file_extention}")
                os.rename(video_default_name, video_name)
                audio_name = audio.download(output_path=tempdir, max_retries=10)
                print(f"{video_title} downloaded successfully")
                combined_name = os.path.join(tempdir, f'{event.id}_combined{file_extention}')
                combine_video_audio(video_name, audio_name, combined_name)
                if do_trim:
                    output_name = os.path.join(tempdir, f'{event.id}_out{file_extention}')
                    trim(combined_name, output_name, start=start, end=end)
                else:
                    output_name = combined_name
            msg = f"#Bot #Youtube " + msg_extra
            msg += f"\n{video_title}\nLink: {url}"
            msg += f"\nStart: {datetime.timedelta(seconds=start)}, End: {datetime.timedelta(seconds=end)}"
            if not args.onlyaudio:
                if not (args.noaudio or args.gif) and stream:
                    msg += f"\nResolution: {stream.resolution}"
                else:
                    msg += f"\nResolution: {video.resolution}"
            await event.respond(msg, link_preview=False, file=output_name, nosound_video=nosound_video)
            await message.delete()
            await event.message.delete()
    except (http.client.IncompleteRead) as e:
        print(e)
        await message.delete()
        await download_youtube(event, url, resolution, start, end)
    except Exception as e:
        print(e)
        msg = "#Bot: failed to download video."
        await abort_and_reply(msg, message, event)

if __name__ == '__main__':
    client.run_until_disconnected()
