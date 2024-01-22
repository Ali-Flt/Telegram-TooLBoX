docker run --rm -it --network host -v "$PWD":/app -w /app telegram_toolbox python3 create_telegram_session.py --config config.yaml
