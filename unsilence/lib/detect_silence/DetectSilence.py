import trace
import numpy as np
import torch
from silero_vad import load_silero_vad, read_audio, get_speech_timestamps
import re
import subprocess
from pathlib import Path
import json
from unsilence.lib.intervals.Intervals import Intervals, Interval
import os
import shutil
import soundfile as sf
import traceback
from unsilence.lib.render_media.MediaRenderer import MediaRenderer
import torchaudio

import torch
torch.set_num_threads(1)

from IPython.display import Audio
from pprint import pprint
# download example
USE_ONNX = True
try:
    from silero_vad import (load_silero_vad,
                            read_audio,
                            get_speech_timestamps,
                            save_audio,
                            VADIterator,
                            collect_chunks)
    model = load_silero_vad(onnx=USE_ONNX)
except Exception as e:
    print(str(e))
    model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                    model='silero_vad',
                                    force_reload=True,
                                        onnx=USE_ONNX)

    (get_speech_timestamps,
    save_audio,
    read_audio,
    VADIterator,
    collect_chunks) = utils


def detect_silence_vad(input_file, media_duration=0):
    """
    from silero_vad import load_silero_vad, read_audio, get_speech_timestamps
    model = load_silero_vad()
    wav = read_audio('path_to_audio_file') # backend (sox, soundfile, or ffmpeg) required!
    speech_timestamps = get_speech_timestamps(wav, model)
    """
    global model, enumerator_value
    temp = Path.cwd() / f'temp{enumerator_value}.wav'
    try:
        os.remove(temp)
    except:
        pass
    enumerator_value += 1
    tmp = str(input_file)
    if '.mp4' in tmp or '.mov' in tmp or '.mpg' in tmp or '.avi' in tmp:
        convert_video_to_audio(input_file, temp)
    elif ".wav" in tmp:
        shutil.copy(input_file, temp)
    # model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad')
    # (get_speech_timestamps, _, read_audio, _, _) = utils
    # this assumes that you have a relevant version of PyTorch installed

    SAMPLING_RATE = 16000

    wav, sample_rate = load_audio(temp)
    speech_timestamps = get_speech_timestamps(wav, model)
    try:
        os.remove(temp)
    except Exception as e:
        print(str('error erasing wav file'))
    return convert_intervals(speech_timestamps, sample_rate)
    
def detect_silence(input_file: Path, **kwargs):
    """
    Detects silence in a file and outputs the intervals (silent/not silent) as a lib.Intervals.Intervals object
    :param input_file: File where silence should be detected
    :param kwargs: Various Parameters, see below
    :return: lib.Intervals.Intervals object

    kwargs:
        silence_level: Threshold of what should be classified as silent/audible (default -35) (in dB)
        silence_time_threshold: Resolution of the ffmpeg detection algorithm (default 0.5) (in seconds)
        short_interval_threshold : The shortest allowed interval length (default: 0.3) (in seconds)
        stretch_time: Time the interval should be enlarged/shrunken (default 0.25) (in seconds)
        on_silence_detect_progress_update: Function that should be called on progress update
            (called like: func(current, total))
    """
    input_file = Path(input_file).absolute()
    # if input_file:
    #     return detect_silence_vad(input_file)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file {input_file} does not exist!")

    try:
        silent_detect_progress_update = kwargs.get("on_silence_detect_progress_update", None)
    except Exception as e:
        traceback.print_exc(e)

    intervals = Intervals()
    media_duration = None
    intervals, media_duration = detect_silence_vad(input_file, media_duration)


    if silent_detect_progress_update is not None:
        silent_detect_progress_update(media_duration, media_duration)

    intervals.optimize(
        kwargs.get('short_interval_threshold', 0.3),
        kwargs.get('stretch_time', 0.25)
    )

    return intervals

enumerator_value = 0 

def convert_video_to_audio(video_file, audio_output):
    global enumerator_value
    cmd = [
        "ffmpeg",
        '-y',
        "-i", str(video_file),
        "-vn",  # No video.
        "-acodec", "pcm_s16le",  # Set codec to PCM s16 le
        "-ar", "16000",  # Audio sample rate
        "-ac", "1",  # Stereo
        audio_output
    ]
    subprocess.run(cmd, check=True)
    return audio_output


def load_audio(file_path):
    data, samplerate = sf.read(file_path, dtype='float32')
    if data.ndim > 1:
        data = data.mean(axis=1)  # Convert to mono by averaging channels
    data = torch.tensor(data)
    return data, 16000  # Return tensor and new samplerate

def convert_intervals(speech_timestamps, sample_rate, media_duration=0):
    """
    Converts speech timestamps into intervals of silence and speech, matching the logic used for handling VAD outputs.

    Arguments:
    - speech_timestamps: A list of dictionaries, each with 'start' and 'end' keys, representing sample indices in the audio.
    - sample_rate: The sample rate of the audio data, used to convert indices to seconds.
    - media_duration: Total duration of the media in seconds.

    Returns:
    - An Intervals object with integrated speech and non-speech intervals.
    """
    intervals = Intervals()
    current_interval = Interval(start=0, end=0, is_silent=True)  # Start assuming initial silence

    for ts in speech_timestamps:
        start_sec = round(ts['start'] / sample_rate, 2)
        end_sec = round(ts['end'] / sample_rate, 2)
        
        # Handle the transition to the speech interval
        if current_interval.start != start_sec:
            current_interval.end = start_sec
            intervals.add_interval(current_interval)
            current_interval = Interval(start=start_sec, is_silent=False)

        # Handle the transition to the silence interval after speech
        current_interval.end = end_sec
        intervals.add_interval(current_interval)
        current_interval = Interval(start=end_sec, is_silent=True)

    # Handle any trailing silence after the last spee
    # Determine media duration from the last timestamp
    if len(speech_timestamps) > 0:
        media_duration = speech_timestamps[len(speech_timestamps)-1]['end'] / sample_rate

    # Handle any trailing silence after the last speech interval
    current_interval.end = media_duration
    intervals.add_interval(current_interval)

    return intervals, media_duration





if __name__ == "__main__":
    inputfile = r"C:\Users\dower\Videos\Chilli16401-17461.mp4"
    # print(str(detect_silence_vad(r"C:\Users\dower\Videos\h-16401-17461.mp4")))
    intervals, current_interval, media_duration = detect_silence_vad(inputfile)
    obj = MediaRenderer('\\temp\\')
    output_file = inputfile.replace('.mp4', '_unsilenced.mp4')
    obj.render(inputfile, output_file, intervals)
