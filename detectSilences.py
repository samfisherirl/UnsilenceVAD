from pprint import pprint
from IPython.display import Audio
import numpy as np
import torch
from silero_vad import load_silero_vad, read_audio, get_speech_timestamps
import subprocess
from pathlib import Path
from unsilence.lib.intervals.Intervals import Intervals, Interval
import os
import shutil
import soundfile as sf
import traceback
from unsilence.lib.render_media.MediaRenderer import MediaRenderer
import site


import torch
torch.set_num_threads(1)


def printer(string):
    print(f'\n\n##################\n{string}\n##################\n\n')


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
    try:
        model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                      model='silero_vad',
                                      force_reload=True,
                                      onnx=USE_ONNX)
    except Exception as e:
        printer('unable to load onnx cpu model #2')
        from silero_vad import (load_silero_vad,
                                read_audio,
                                get_speech_timestamps,
                                save_audio,
                                VADIterator,
                                collect_chunks)
        model = load_silero_vad(onnx=False)


def detect_silence_vad(input_file, media_duration=0):
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
    speech_timestamps = get_speech_timestamps(wav, model, return_seconds=True)
    try:
        os.remove(temp)
    except Exception as e:
        print(str('error erasing wav file'))
    return speech_timestamps


def detect_silence(input_file: Path, **kwargs):
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
        str(audio_output)
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
        start_sec = round((ts['start'] / sample_rate), 3)
        end_sec = round((ts['end'] / sample_rate), 3)

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


def convert_intervals(speech_timestamps, sample_rate, media_duration=0):
    """
    Converts speech timestamps into intervals of silence and speech, matching the logic used for handling VAD outputs.
    Ensures no trailing silence is added if the last speech interval ends at the media duration.

    Arguments:
    - speech_timestamps: A list of dictionaries, each with 'start' and 'end' keys, representing sample indices in the audio.
    - sample_rate: The sample rate of the audio data, used to convert indices to seconds.
    - media_duration: Total duration of the media in seconds.

    Returns:
    - An Intervals object with integrated speech and non-speech intervals.
    - Actual media duration based on VAD output, or provided duration.
    """
    intervals = Intervals()
    current_interval = Interval(start=0, end=0, is_silent=True)  # Start assuming initial silence

    for ts in speech_timestamps:
        start_sec = round((ts['start'] / sample_rate), 3)
        end_sec = round((ts['end'] / sample_rate), 3)

        # Handle transition to speech interval
        if current_interval.end != start_sec:  # Check if there's a gap
            if current_interval.end != 0:
                intervals.add_interval(current_interval)
            current_interval = Interval(start=current_interval.end, end=start_sec, is_silent=True)
            intervals.add_interval(current_interval)
            current_interval = Interval(start=start_sec, is_silent=False)
        current_interval.end = end_sec

    # Still ensure to add the last interval if it's speech
    if not current_interval.is_silent:
        intervals.add_interval(current_interval)
        # Update the current_interval to start from the end of speech
        current_interval = Interval(start=start_sec, end=media_duration, is_silent=True)

    # Compare the VAD-determined end with the actual media duration and adjust if necessary
    if current_interval.start < media_duration:
        current_interval.end = media_duration
        intervals.add_interval(current_interval)
    return intervals, media_duration


def get_media_duration(media_file):
    """
    Uses ffmpeg to determine the duration of a media file (audio or video).

    Arguments:
    - media_file: Path to the media file.

    Returns:
    - Duration of the media in seconds as a float.
    """
    cmd = [
        "ffmpeg",
        "-i", media_file,
        "-hide_banner",
        "-f", "ffmetadata",
        "-"
    ]

    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    output, err = process.communicate()

    # ffmpeg outputs media details to the stderr
    output = err.decode("utf-8")

    # Find the duration from the ffmpeg output
    lines = output.split('\n')
    duration = 0.0
    for line in lines:
        if "Duration" in line:
            duration_line = line.split(",")[0]  # Extracts the duration section
            time_str = duration_line.split("Duration:")[1].strip()
            time_parts = time_str.split(":")
            hours = float(time_parts[0])
            minutes = float(time_parts[1])
            seconds = float(time_parts[2])
            duration = 3600 * hours + 60 * minutes + seconds
            break

    return duration


if __name__ == "__main__":
    inputfile = r"C:\Users\dower\Downloads\Kickstarter Crap - Rocket S.mp4"
    # print(str(detect_silence_vad(r"C:\Users\dower\Videos\h-16401-17461.mp4")))
    intervals, media_duration = detect_silence_vad(inputfile, get_media_duration(inputfile))
    obj = MediaRenderer('\\temp\\')
    output_file = inputfile.replace('.mp4', '_unsilenced.mp4')
    obj.render(inputfile, output_file, intervals)
