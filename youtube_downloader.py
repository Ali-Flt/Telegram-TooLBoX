from pytube import YouTube, helpers
import ffmpeg
import os, errno
import re
import yaml
import argparse
from telethon import TelegramClient, events

url_pattern = "(https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z]{2,}(\.[a-zA-Z]{2,})(\.[a-zA-Z]{2,})?\/[a-zA-Z0-9]{2,}|((https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z]{2,}(\.[a-zA-Z]{2,})(\.[a-zA-Z]{2,})?)|(https:\/\/www\.|http:\/\/www\.|https:\/\/|http:\/\/)?[a-zA-Z0-9]{2,}\.[a-zA-Z0-9]{2,}\.[a-zA-Z0-9]{2,}(\.[a-zA-Z0-9]{2,})?"
youtube_url_pattern = "^((?:https?:)?//)?((?:www|m).)?((?:youtube.com|youtu.be))(/(?:[\w-]+?v=|embed/|v/|shorts/)?)([\w-]+)(\S+)?.*"
parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.yaml')
args = parser.parse_args()

config = {}
with open(args.config) as f:
    config = yaml.load(f, Loader=yaml.loader.SafeLoader)

allowed_users = config['allowed_users']
allowed_chats = config['allowed_chats']

proxy = None
if config['proxy']:
    proxies = {"http": f"{config['proxy']['proxy_type']}://{config['proxy']['addr']}:{config['proxy']['port']}",
               "https": f"{config['proxy']['proxy_type']}://{config['proxy']['addr']}:{config['proxy']['port']}"}
    helpers.install_proxy(proxies)
    proxy = config['proxy']

client = TelegramClient(config['session'], config['api_id'], config['api_hash'], proxy=proxy).start(phone=config['phone_number'])


def silentremove(filename):
    try:
        os.remove(filename)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

def trim(input_path, output_path, start, end):
    input_stream = ffmpeg.input(input_path)

    vid = (
        input_stream.video
        .trim(start=start, end=end)
        .setpts('PTS-STARTPTS')
    )
    aud = (
        input_stream.audio
        .filter_('atrim', start=start, end=end)
        .filter_('asetpts', 'PTS-STARTPTS')
    )

    joined = ffmpeg.concat(vid, aud, v=1, a=1).node
    output = ffmpeg.output(joined[0], joined[1], output_path, loglevel="quiet")
    output.run(overwrite_output=True)

def parse_args(text):
    resolution = None
    start = None
    end = None
    url = None
    try:
        splitted_message = re.split(' ', text)
        url = splitted_message[0]
        if len(splitted_message) == 2:
            resolution = splitted_message[1]
        elif len(splitted_message) == 3:
            start = int(splitted_message[1])
            end = int(splitted_message[2])
        elif len(splitted_message) == 4:
            resolution = splitted_message[1]
            start = int(splitted_message[2])
            end = int(splitted_message[3])
    except:
        pass
    return url, resolution, start, end

@client.on(events.NewMessage(func=lambda e: e.chat_id in allowed_chats or e.sender.username in allowed_users, pattern=youtube_url_pattern))
async def handler(event):
    text = event.text
    id = event.chat_id
    print(id)
    url, resolution, start, end = parse_args(text)
    if url is not None:
        await download_vid(id, url, resolution, start, end)
    else:
        print("invalid input.")

async def download_vid(id, url, resolution=None, start=None, end=None):
    try:
        yt = YouTube(url)
        video_title = yt.title
        print(f"Downloading {video_title} ...")
        streams = yt.streams.filter(progressive=True)
        if resolution is not None:
            if len(streams.filter(res=resolution)):
                stream = streams.filter(res=resolution).first()
            else:
                stream = streams.get_highest_resolution()
        else:
            stream = streams.first()
        if stream:
            stream.download()
            print("Downloading .....")
            print(f"{video_title} downloaded successfully")
            input_name = stream.default_filename
            file_name = os.path.splitext(input_name)[0]
            file_extention = os.path.splitext(input_name)[-1]
            
            if start is not None:
                output_name =  f'{file_name}_out{file_extention}'
                trim(input_name, output_name, start=start, end=end)
            else:
                output_name = input_name
            await client.send_message(id, f"{video_title}", file=output_name)
            silentremove(input_name)
            silentremove(output_name)
        else:
            print("video not found.")
    except:
        print("failed to download video.")

client.run_until_disconnected()