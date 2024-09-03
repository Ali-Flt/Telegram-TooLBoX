import os
import re
import yaml
import argparse
from telethon import TelegramClient, events
import datetime
import tempfile
import http
from urllib.error import HTTPError
from src.utils import get_timestamp, get_valid_resolution, merge_lists

async def abort_and_reply(msg, msg_to_delete, event):
    await msg_to_delete.delete()
    print(msg)
    await event.reply(msg)
    
max_retries = 10
author_msg = '__Telegram TooLBoX by @a_flt__'
url_pattern = "(https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z]{2,}(\.[a-zA-Z]{2,})(\.[a-zA-Z]{2,})?\/[a-zA-Z0-9]{2,}|((https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z]{2,}(\.[a-zA-Z]{2,})(\.[a-zA-Z]{2,})?)|(https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z0-9]{2,}\.[a-zA-Z0-9]{2,}\.[a-zA-Z0-9]{2,}(\.[a-zA-Z0-9]{2,})?"
youtube_url_pattern = "^((?:https?:)?//)?((?:www|m).)?((?:youtube.com|youtu.be))(/(?:[\w-]+?v=|embed/|v/|shorts/)?)([\w-]+)(\S+)?.*"
instagram_url_pattern = "(?:(?:http|https):\/\/)?(?:www\.)?(?:instagram\.com|instagr\.am)\/([A-Za-z0-9-_\.]+).*"
make_clip_pattern = "^clip.*"
help_pattern = "^/(start|help)$"
allowed_resolutions = ['2160', '1440', '1080', '720', '480', '360', '240', '144']

yt_parser = argparse.ArgumentParser(add_help=False, prog='youtube_media_url', exit_on_error=False)
yt_parser.add_argument('-0', dest='disable', action='store_const', const=True, default=False, help="ignore command")
yt_parser.add_argument('-r', dest='resolution', type=str, help="video resolution (e.g. 1080)")
yt_parser.add_argument('-s', dest='start', type=str, help="start time in seconds or MM:SS")
yt_parser.add_argument('-e', dest='end', type=str, help="end time in seconds, MM:SS")
yt_parser.add_argument('-d', dest='duration', type=str, help="duration time in seconds, MM:SS")
yt_parser.add_argument('-ao', dest='onlyaudio', action='store_const', const=True, default=False, help="get only audio stream")
yt_parser.add_argument('-vo', dest='noaudio', action='store_const', const=True, default=False, help="get only video stream")
yt_parser.add_argument('-gif', dest='gif', action='store_const', const=True, default=False, help="convert video to gif")
yt_parser.add_argument('-rm', dest='rm', action='store_const', const=True, default=False, help="delete original command message after downloading")
yt_parser.add_argument('-h', dest='help', action='store_const', const=True, default=False, help="print this help command")

insta_parser = argparse.ArgumentParser(add_help=False, prog='instagram_media_url', exit_on_error=False)
insta_parser.add_argument('-0', dest='disable', action='store_const', const=True, default=False, help="ignore command")
insta_parser.add_argument('-rm', dest='rm', action='store_const', const=True, default=False, help="delete original command message after downloading")
insta_parser.add_argument('-h', dest='help', action='store_const', const=True, default=False, help="print this help command")

clip_parser = argparse.ArgumentParser(add_help=False, prog='clip', exit_on_error=False)
clip_parser.add_argument('-0', dest='disable', action='store_const', const=True, default=False, help="ignore command")
clip_parser.add_argument('-rm', dest='rm', action='store_const', const=True, default=False, help="delete original command message after downloading")
clip_parser.add_argument('-h', dest='help', action='store_const', const=True, default=False, help="print this help command")
clip_parser.add_argument('-s', dest='start', type=str, help="start time in seconds or MM:SS")
clip_parser.add_argument('-e', dest='end', type=str, help="end time in seconds, MM:SS")
clip_parser.add_argument('-d', dest='duration', type=str, help="duration time in seconds, MM:SS")
clip_parser.add_argument('-vo', dest='noaudio', action='store_const', const=True, default=False, help="get only video stream")
clip_parser.add_argument('-gif', dest='gif', action='store_const', const=True, default=False, help="convert video to gif")

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
allowed_clip_user_ids = config['allowed_clip_user_ids']
allowed_clip_chat_ids = config['allowed_clip_chat_ids']
allowed_stt_user_ids = config['allowed_stt_user_ids']
allowed_stt_chat_ids = config['allowed_stt_chat_ids']

if len(allowed_youtube_user_ids) > 0 or len(allowed_youtube_chat_ids) > 0:
    from src.yt_utils import get_yt_video_info, download_yt_dlp

if len(allowed_youtube_user_ids) > 0 or len(allowed_youtube_chat_ids) > 0 or len(allowed_clip_user_ids) > 0 or len(allowed_clip_chat_ids) > 0:
    from src.video_utils import get_video_length, remove_audio, trim

if len(allowed_insta_user_ids) > 0 or len(allowed_clip_chat_ids) > 0:
    from instagrapi import Client
    insta = Client()
else:
    insta = None

if len(allowed_stt_user_ids) > 0 or len(allowed_stt_chat_ids) > 0:
    from src.stt_utils import get_stt_model
    stt_model = get_stt_model()
    
all_allowed_user_ids = merge_lists(allowed_youtube_user_ids, allowed_insta_user_ids, allowed_clip_user_ids, allowed_stt_user_ids)
all_allowed_chat_ids = merge_lists(allowed_youtube_chat_ids, allowed_insta_chat_ids, allowed_clip_chat_ids, allowed_stt_chat_ids)


proxy = None
proxies = None
proxy_str = None
if config['proxy']:
    proxy_str = f"{config['proxy']['proxy_type']}://{config['proxy']['addr']}:{config['proxy']['port']}"
    proxies = {"http": proxy_str,
               "https": proxy_str}
    proxy = config['proxy']
    if insta is not None:
        insta.set_proxy(proxy_str)

client = TelegramClient(config['session'], config['api_id'], config['api_hash'], proxy=proxy).start(bot_token=config['bot_token'])

if config['instagram_session_id'] and insta is not None:
    insta.login_by_sessionid(config['instagram_session_id'])

@client.on(events.NewMessage(func=lambda e: e.chat_id in all_allowed_chat_ids or e.sender_id in all_allowed_user_ids, pattern=help_pattern))
async def hanlder_help(event):
    msg = "Please use one of the following commands: (You may not have access to all commands.)"
    msg += f"\n`{yt_parser.format_help()}`"
    msg += "\n------------------------------------------------------------------------------------------------"
    msg += f"\n`{insta_parser.format_help()}`"
    msg += "\n------------------------------------------------------------------------------------------------"
    msg += f"\n`{clip_parser.format_help()}`"
    msg += "\n------------------------------------------------------------------------------------------------"
    msg += f"\n{author_msg}"
    await event.respond(msg)

@client.on(events.NewMessage(func=lambda e: (e.chat_id in allowed_stt_chat_ids or e.sender_id in allowed_stt_user_ids) and e.message.voice))
async def handler_stt(event):
    try:
        with tempfile.TemporaryDirectory() as tempdir:
            file_name = os.path.join(tempdir, f"{event.id}.mp3")
            await event.message.download_media(file=file_name)
            transcripts = stt_model(file_name)['text']
            await event.reply(f"#Bot #STT\n{transcripts}")
    except Exception as e:
        print(e)
        print("failed to convert speech to text.")

@client.on(events.NewMessage(func=lambda e: e.chat_id in allowed_clip_chat_ids or e.sender_id in allowed_clip_user_ids, pattern=make_clip_pattern))
async def handler_make_clip(event):
    args = parse_args_clip(event.raw_text)
    if args is None:
        return
    if args.help:
        await event.reply(f"`{clip_parser.format_help()}`\nDon't forget to attach the video to your message.\n{author_msg}")
        return
    if args.disable:
        return
    if event.message.video:
        await make_clip(event, args)

def parse_args_clip(text):
    splitted_text = re.split(' ', text)
    try:
        return clip_parser.parse_known_args(splitted_text[1:])[0]
    except Exception as e:
        print(e)
        return None
    
async def make_clip(event, args):
    msg = "#Bot: Creating clip..."
    message = await event.reply(msg)
    print(msg)
    try:
        with tempfile.TemporaryDirectory() as tempdir:
            nosound_video = None
            file_name = os.path.join(tempdir, f"{event.id}.mp4")
            await event.message.download_media(file=file_name)
            length = get_video_length(file_name)
            start = get_timestamp(args.start)
            duration = get_timestamp(args.duration) 
            end = get_timestamp(args.end)
            if start is not None and duration is not None:
                end = start + duration
            elif end is not None and duration is not None:
                start = end - duration
            if start is not None:
                start = max(min(start, length), 0)
            else:
                start = 0
            if end is not None:
                end = max(min(end, length), 0)
            else:
                end = length
            if (start >= end):
                msg = "#Bot: timestamps out of range."
                await abort_and_reply(msg, message, event)
                return
            if end - start < length:
                file_name = trim(file_name, start, end)
            if args.noaudio or args.gif:
                file_name = remove_audio(file_name)
                if args.gif:
                    nosound_video=False
                else:
                    nosound_video=True
            if args.rm:
                await event.respond(f"#Bot #clip_maker", file=file_name, nosound_video=nosound_video)
                await event.message.delete()
            else:
                await event.reply(f"#Bot #clip_maker", file=file_name, nosound_video=nosound_video)
            await message.delete()

    except Exception as e:
        print(e)
        msg = "#Bot: failed to create clip."
        abort_and_reply(msg, message, event)
        
        
@client.on(events.NewMessage(func=lambda e: e.chat_id in allowed_insta_chat_ids or e.sender_id in allowed_insta_user_ids, pattern=instagram_url_pattern))
async def handler_insta(event):
    url, args = parse_args_insta(event.raw_text)
    if args is None:
        return
    if args.help:
        await event.reply(f"`{insta_parser.format_help()}`\n{author_msg}")
        return
    if args.disable:
        return
    if url is not None:
        await download_insta(event, url, args)

def parse_args_insta(text):
    splitted_text = re.split(' ', text)
    try:
        return splitted_text[0], insta_parser.parse_known_args(splitted_text[1:])[0]
    except Exception as e:
        print(e)
        return None, None
    
async def download_insta(event, url, args):
    msg = "#Bot: Downloading Instagram media..."
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
            if args.rm:
                await event.respond(f"#Bot #Instagram\n{caption}\nLink: {url}", link_preview=False, file=media_path)
                await event.message.delete()
            else:
                await event.reply(f"#Bot #Instagram\n{caption}\nLink: {url}", link_preview=False, file=media_path)
            await message.delete()

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
        await event.reply(f"`{yt_parser.format_help()}`\n{author_msg}")
        return
    if args.disable:
        return
    if url is not None:
        await download_youtube(event, url, args, 0)

def parse_args_yt(text):
    splitted_text = re.split(' ', text)
    try:
        return splitted_text[0], yt_parser.parse_known_args(splitted_text[1:])[0]
    except Exception as e:
        print(e)
        return None, None
        
async def download_youtube(event, url, args, retries=0):
    if retries > 0:
        msg = f"#Bot: Failed to download. Retrying ({retries}/{max_retries}) ....."
    else:
        msg = "#Bot: Downloading ....."    
    print(msg)
    message = await event.reply(msg)
    try:
        video_title, is_live, length, base_time = get_yt_video_info(url, proxy_str, config)
        if is_live:
            sign = -1
        else:
            sign = 1
        start = get_timestamp(args.start)
        duration = get_timestamp(args.duration) 
        end = get_timestamp(args.end)
        if start is not None and duration is not None:
            end = start + (sign*duration)
        elif end is not None and duration is not None:
            start = end - (sign*duration)
        if start is not None:
            start = max(min(start, length), 0)
        else:
            if is_live:
                start = length
            else:
                start = 0
        if end is not None:
            end = max(min(end, length), 0)
        else:
            if is_live:
                end = 0
            else:
                end = length
        if (start >= end and not is_live) or (start <= end and is_live):
            msg = "#Bot: timestamps out of range."
            await abort_and_reply(msg, message, event)
            return
        if abs(end-start) > config['max_video_length']:
            msg = f"#Bot: can't download video sections longer than {config['max_video_length']} seconds. Please crop the video shorter."
            await abort_and_reply(msg, message, event)
            return
        resolution = get_valid_resolution(allowed_resolutions, config, args.resolution)
        print(f"Downloading {video_title} ...")
        nosound_video = None
        msg_extra = ''
        mode_id = -1
        with tempfile.TemporaryDirectory() as tempdir:
            ydl_opts = {'proxy': proxy_str,
                        'quiet': True,
                        'overwrites': True,
                        'live_from_start': is_live,
                        'paths': {'temp': tempdir, 'home': tempdir},
                        'cookiefile': config['cookiefile'],
                        'source_address': config['ip_address']
                        }
            if args.onlyaudio:
                mode_id = 0
                msg_extra = '#onlyaudio'
                opts = {
                        'format': 'm4a/ba/b/bv*',
                        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'm4a'}],
                        'final_ext': 'm4a',
                        }
                ydl_opts.update(opts)
                output_file, res, abr = download_yt_dlp(url, ydl_opts, start, end, sign, length, base_time)
            elif args.noaudio or args.gif:
                if args.noaudio:
                    mode_id = 1
                    nosound_video = True
                    msg_extra = '#noaudio'
                else:
                    mode_id = 2
                    nosound_video = False
                    msg_extra = '#gif'
                opts = {
                        'format': f'bv[height<={resolution}]/bv*[height<={resolution}]/b[height<={resolution}]/wv/wv*/w',
                        'final_ext': 'mp4', 
                        'postprocessors': [{'key': 'FFmpegVideoRemuxer', 'preferedformat': 'mp4'}],
                        }
                ydl_opts.update(opts)
                video_file, res, abr = download_yt_dlp(url, ydl_opts, start, end, sign, length, base_time)
                output_file = remove_audio(video_file)
            else:
                mode_id = 3
                opts = {
                        'format': f'bv*[height<={resolution}]+ba/b[height<={resolution}] / wv*+ba/w',
                        'final_ext': 'mp4', 
                        'postprocessors': [{'key': 'FFmpegVideoRemuxer', 'preferedformat': 'mp4'}],
                        }
                ydl_opts.update(opts)
                output_file, res, abr = download_yt_dlp(url, ydl_opts, start, end, sign, length, base_time)
            print(f"{video_title} downloaded successfully")
            msg = f"#Bot #Youtube " + msg_extra
            msg += f"\n{video_title}\nLink: {url}"
            if is_live:
                if length > 43200:
                    start = 'N/A'
                    end = 'N/A'
                else:
                    start = datetime.timedelta(seconds=(length - start))
                    end = datetime.timedelta(seconds=(length - end))
            else:
                start = datetime.timedelta(seconds=start)
                end = datetime.timedelta(seconds=end)
            msg += f"\nStart: {start}, End: {end}"
            if mode_id == 0:
                msg += f"\nBitrate: {abr}Kbps"
            else:
                msg += f"\nResolution: {res}"
            if args.rm:
                await event.respond(msg, link_preview=False, file=output_file, nosound_video=nosound_video)
                await event.message.delete()
            else:
                await event.reply(msg, link_preview=False, file=output_file, nosound_video=nosound_video)
            await message.delete()
    except (http.client.IncompleteRead) as e:
        print(e)
        retries += 1
        if retries < max_retries:
            await message.delete()
            await download_youtube(event, url, resolution, start, end, retries)
        else:
            msg = "#Bot: failed to download video."
            await abort_and_reply(msg, message, event)
    except (HTTPError) as e:
        print(e)
        retries += 1
        if retries < max_retries:
            await message.delete()
            await download_youtube(event, url, resolution, start, end, retries)
        else:
            msg = "#Bot: failed to download video."
            await abort_and_reply(msg, message, event)
    except Exception as e:
        print(e)
        msg = "#Bot: failed to download video."
        await abort_and_reply(msg, message, event)

if __name__ == '__main__':
    client.run_until_disconnected()

