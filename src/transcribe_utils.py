from googletrans import Translator
from multiprocessing import Process, Queue
import whisper
from whisper.utils import get_writer
import os

def transcribe_audio(audio_file):
    model = whisper.load_model("large")
    transcript = model.transcribe(audio_file, word_timestamps=True)
    dir = os.path.dirname(audio_file)
    name = os.path.basename(audio_file)
    no_ext_name = os.path.splitext(name)[0]
    word_options = {
    "highlight_words": False,
    "max_line_count": 3,
    "max_words_per_line": 6
    }
    srt_writer = get_writer("srt", dir)
    srt_writer(transcript, name, word_options)
    word_options["highlight_words"] = False
    srt_writer = get_writer("srt", dir)
    srt_writer(transcript, name, word_options)
    return os.path.join(dir, f"{no_ext_name}.srt")

def translate(input_text, src='en', dest='fa'):
    translator = Translator()
    return translator.translate(input_text, src=src, dest=dest).text

def transcribe_worker(queue, input):
    srt_file = transcribe_audio(input)
    queue.put(srt_file)
    
def translate_worker(queue, input):
    result = translate(input)
    queue.put(result)
    
def run_transcribe(input_audio):
    queue = Queue()
    p = Process(target=transcribe_worker, args=(queue, input_audio))
    p.start()
    p.join()
    return queue.get()
    
def run_translate(input_text):
    queue = Queue()
    p = Process(target=translate_worker, args=(queue, input_text))
    p.start()
    p.join()
    return queue.get()

