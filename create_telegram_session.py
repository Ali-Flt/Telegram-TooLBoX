from telethon.sync import TelegramClient
import argparse
import yaml

parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.yaml')
args = parser.parse_args()

config = {}
with open(args.config) as f:
    config = yaml.load(f, Loader=yaml.loader.SafeLoader)
proxy = None
if config['proxy']:
    proxy = config['proxy']
    
client = TelegramClient(config['session'], config['api_id'], config['api_hash'], proxy=proxy).start(bot_token=config['bot_token'])

print('.session file created successfully. DO NOT SHARE IT!')

