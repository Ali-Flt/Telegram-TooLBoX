import warnings
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")

@torch.no_grad()
def speech_to_text(audio_input):
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    model_id = "openai/whisper-large-v3"

    model = AutoModelForSpeechSeq2Seq.from_pretrained(model_id,
                                                      torch_dtype=torch_dtype,
                                                      low_cpu_mem_usage=True,
                                                      use_safetensors=True,
                                                      device_map='auto'
                                                      )
    model.eval()
    model.generation_config.language = "persian"
    model.generation_config.task = "transcribe"
    processor = AutoProcessor.from_pretrained(model_id)
    model.generation_config.forced_decoder_ids = None
    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        torch_dtype=torch_dtype
    )
    return pipe(audio_input)['text']

def stt_worker(queue, audio_input):
    result = speech_to_text(audio_input)
    queue.put(result)
