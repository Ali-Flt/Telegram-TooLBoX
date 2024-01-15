# Telegram TooLBoX
Several ease of use tools for telegram.

# Tools
- Download media from youtube. Use `https://www.youtube.com/video_id -h` for help
- Download media from instagram. Use `https://www.instagram.com/video_id -h` for help
- Convert videos to gif. Use `gif -h` for help

# How to use
1. create `config.yaml` based on `config.yaml.example` (skip the allowed_user_ids parameters at this step)
2. run `./build_docker_image.sh`
3. run `./get_user_ids.sh` and store the results in config.yaml
4. run `./create_telegram_session.sh` and enter the asked code
5. run `docker compose up`

# Donations
Consider buying me a coffee if this helped you.

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/aflt)
