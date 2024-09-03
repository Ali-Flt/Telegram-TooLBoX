import ffmpeg
import os
import datetime
import subprocess

def remove_audio(video_file):
    file_name = os.path.splitext(video_file)[0]
    ext = os.path.splitext(video_file)[-1]
    output_file = f"{file_name}_noaudio{ext}"
    video_stream = ffmpeg.input(video_file)
    ffmpeg.output(video_stream, output_file, vcodec='copy', an=None, loglevel='quiet').run(overwrite_output=True)
    return output_file

def trim(video_file, start, end):
    file_name = os.path.splitext(video_file)[0]
    ext = os.path.splitext(video_file)[-1]
    output_file = f"{file_name}_trimmed{ext}"
    input_stream = ffmpeg.input(video_file, ss=(str(datetime.timedelta(seconds=start))), to=(str(datetime.timedelta(seconds=end))))
    ffmpeg.output(input_stream, output_file, acodec='copy', vcodec='copy', loglevel='quiet').run(overwrite_output=True)
    return output_file

def get_video_length(input_video):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', input_video], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return float(result.stdout)
