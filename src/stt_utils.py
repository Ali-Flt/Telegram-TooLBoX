import warnings
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline #, MarianMTModel, MarianTokenizer
from googletrans import Translator
from multiprocessing import Process, Queue


warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")

fa_model_id = "openai/whisper-large-v3"
en_model_id = "openai/whisper-large-v3"
translate_model_id = "Helsinki-NLP/opus-mt-en-iir"

@torch.no_grad()
def speech_to_text(audio_input, model_id, lang):
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForSpeechSeq2Seq.from_pretrained(model_id,
                                                      torch_dtype=torch_dtype,
                                                      low_cpu_mem_usage=True,
                                                      use_safetensors=True,
                                                      device_map='auto'
                                                      )
    model.eval()
    model.generation_config.language = lang
    model.generation_config.task = "transcribe"
    processor = AutoProcessor.from_pretrained(model_id)
    model.generation_config.forced_decoder_ids = None
    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        torch_dtype=torch_dtype,
        return_timestamps=True
    )
    return pipe(audio_input)['text']

@torch.no_grad()
def translate(input_text, src='en', dest='fa'):
    translator = Translator()
    return translator.translate(input_text, src=src, dest=dest).text

    # tokenizer = MarianTokenizer.from_pretrained(model_id)
    # model = MarianMTModel.from_pretrained(model_id)
    # tokens = tokenizer(input_text, return_tensors="pt", padding=True, truncation=True)
    # translated_tokens = model.generate(**tokens)
    # return tokenizer.decode(translated_tokens[0], skip_special_tokens=True)

def stt_worker(queue, input, lang="persian"):
    if lang == "persian":
        model = fa_model_id
    else:
        model = en_model_id
    result = speech_to_text(input, model_id=model, lang=lang)
    queue.put(result)
    
def translate_worker(queue, input):
    result = translate(input)
    queue.put(result)
    
def run_stt(input_audio, lang="persian"):
    queue = Queue()
    p = Process(target=stt_worker, args=(queue, input_audio, lang))
    p.start()
    p.join()
    return queue.get()
    
def run_translate(input_text):
    queue = Queue()
    p = Process(target=translate_worker, args=(queue, input_text))
    p.start()
    p.join()
    return queue.get()

