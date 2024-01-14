# youtube-dl-telegram
Automatically download youtube videos and send it to the corresponding telegram chat.

# How to use

1. create `config.yaml` based on `config.yaml.example`
2. run `./build_docker_image.sh`
3. run `./create_telegram_session.sh` and enter the asked code
4. run `docker compose up`

send youtube links in one of these formates:
1. link
2. link resolution
3. link start_time end_time
4. link resolution start_time end_time

- resolution example: `1080p`, `720p`, ...
- start_time and end_time are in seconds.