docker run --rm -it --network host -v "$PWD":/app -w /app yt_insta_downloader python3 create_telegram_session.py --config config.yaml
