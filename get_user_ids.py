from telethon import TelegramClient, sync
import yaml
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.yaml')
args = parser.parse_args()

config = {}
with open(args.config) as f:
    config = yaml.load(f, Loader=yaml.loader.SafeLoader)
    
    
proxy = None
if config['proxy']:
    proxy_str = f"{config['proxy']['proxy_type']}://{config['proxy']['addr']}:{config['proxy']['port']}"
    proxies = {"http": proxy_str,
               "https": proxy_str}
    proxy = config['proxy']

client = TelegramClient(config['session'], config['api_id'], config['api_hash'], proxy=proxy).start(bot_token=config['bot_token'])

if __name__ == '__main__':
    allowed_youtube_user_ids = []
    allowed_insta_user_ids = []
    allowed_clip_user_ids = []
    
    with client:
        for user in config['allowed_youtube_usernames']:
            entity = client.get_entity(user)
            allowed_youtube_user_ids.append(entity.id)
        for user in config['allowed_insta_usernames']:
            entity = client.get_entity(user)
            allowed_insta_user_ids.append(entity.id)
        for user in config['allowed_clip_usernames']:
            entity = client.get_entity(user)
            allowed_clip_user_ids.append(entity.id)
        
    print(f"allowed_youtube_user_ids: {allowed_youtube_user_ids}")
    print(f"allowed_insta_user_ids: {allowed_insta_user_ids}")
    print(f"allowed_clip_user_ids: {allowed_clip_user_ids}")

