import time
from unsilence import Unsilence
from pathlib import Path
import traceback
import tkinter as tk
from tkinter import ttk, filedialog
import sv_ttk
import os
from dotenv import load_dotenv, dotenv_values, set_key
import subprocess
import json
import datetime
import shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from jumpcutter import jumpcutter
import detectSilences
import fffmpHandler

SPLIT_DISTANCE = 180  # 30 minutes
DISTANCE_THRESHOLD = {'SHORT': 0.3, 'STRETCH': 0.25}


def get_video_length(video_path):
    cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"{video_path}\""
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    return float(result.stdout.strip())


def remove_file_if_exists(file_path):
    # Check if the file exists
    if os.path.exists(file_path):
        # Remove the file
        os.remove(file_path)
        print(f"File {file_path} has been removed.")
    else:
        print(f"File {file_path} does not exist.")


def split_video(video_path):
    current_time = datetime.now().strftime("%H-%M-%S")
    dirname = Path(video_path).parent / f"tmp_{current_time}"

    # Ensure the temporary directory is clean
    if dirname.exists():
        shutil.rmtree(dirname)
    dirname.mkdir(parents=True, exist_ok=True)  # Create temporary directory

    filename, ext = os.path.splitext(Path(video_path).name)
    segment_files = []
    output_paths = []

    # Execute ffmpeg command to split the video
    split_cmd = f'ffmpeg -i "{video_path}" -c copy -map 0 -segment_time {SPLIT_DISTANCE} -f segment -reset_timestamps 1 "{dirname}/{filename}_%03d{ext}"'
    subprocess.run(split_cmd, shell=True)

    # List all files in tmp directory
    files = list(dirname.glob(f"{filename}_*{ext}"))
    for file in files:
        segment_files.append(str(file))
        output_paths.append(str(file).replace(f"{file.name}", f"{file.stem}_NODEADAIR{ext}"))

    return segment_files, output_paths


def handle_unsilence(file_path, speed, silence_level, output_path):
    cwd = Path.cwd()
    remove_file_if_exists(output_path)
    try:
        u = Unsilence(file_path)
        u.detect_silence()
        estimated_time = u.estimate_time(silent_speed=int(speed))  # Estimate time savings
        printer(json.dumps(estimated_time, indent=2))
        printer('rendering media')
        u.render_media(f"{output_path}", silence_volume=silence_level)  # No options specified
        printer('rendering media done')
    except Exception as e:
        traceback.format_exception(e)


def process_videos(video_params_list, max_threads):
    """
    Process multiple videos using handle_unsilence function with threading.

    :param video_params_list: List of tuples, each containing parameters for handle_unsilence (file_path, speed, silence_level, output_path).
    :param max_threads: Maximum number of threads to use for parallel processing.
    """
    with ThreadPoolExecutor(max_workers=int(max_threads)) as executor:
        # Create a list to hold the futures
        futures = [
            executor.submit(handle_unsilence, *params)
            for params in video_params_list
        ]

        # Iterate over the futures as they complete (as_completed returns an iterator)
        for future in as_completed(futures):
            future.result()  # This will re-raise any exceptions caught during the threading execution


def combine_videos(video_paths, output_path):
    # Create a file containing all video file paths to concatenate
    with open("filelist.txt", "w") as file:
        for path in video_paths:
            file.write(f"file '{path}'\n")
    # Combine videos using ffmpeg
    combine_cmd = f"ffmpeg -f concat -safe 0 -i filelist.txt -c copy -y \"{output_path}\""
    subprocess.run(combine_cmd, shell=True)
    os.remove("filelist.txt")  # Clean up file list


def ensure_env_file_exists():
    env_path = ".env"
    if not os.path.exists(env_path):
        open(env_path, 'a').close()  # Create the .env file if it does not exist


def printer(string):
    print(f'\n\n##################\n{string}\n##################\n\n')


class VideoProcessorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        global DISTANCE_THRESHOLD
        self.title("Video Processor")
        self.geometry("600x300")
        load_dotenv()  # Load environment variables

        sv_ttk.set_theme("dark")

        # Set styles
        style = ttk.Style()
        style.configure("TLabel", font=("Arial", 12))
        style.configure("TButton", font=("Arial", 12))
        style.configure("TEntry", font=("Arial", 12))

        # Create widgets
        ttk.Label(self, text="Silence Fast Forward Speed:").grid(column=0, row=0, sticky="w", padx=10, pady=5)
        self.speed_entry = ttk.Entry(self, font=("Arial", 12))
        self.speed_entry.insert(0, dotenv_values().get("SPEED", "16"))
        self.speed_entry.grid(column=1, row=0, padx=10, pady=5)

        ttk.Label(self, text="Select Video File:").grid(column=0, row=1, sticky="w", padx=10, pady=5)
        self.file_path_entry = ttk.Entry(self, font=("Arial", 12))
        self.file_path_entry.insert(0, dotenv_values().get("FILE_PATH", ""))
        self.file_path_entry.grid(column=1, row=1, padx=10, pady=5)
        ttk.Button(self, text="Browse", command=self.browse_file).grid(column=2, row=1, padx=10, pady=5)

        ttk.Label(self, text="Number of Threads:").grid(column=0, row=2, sticky="w", padx=10, pady=5)
        self.thread_num_entry = ttk.Entry(self, font=("Arial", 12))
        self.thread_num_entry.insert(0, dotenv_values().get("THREADS", "2"))
        self.thread_num_entry.grid(column=1, row=2, padx=10, pady=5)

        ttk.Label(self, text="Minimum Silence Level (dB):").grid(column=0, row=3, sticky="w", padx=10, pady=5)
        self.silence_level_entry = ttk.Entry(self, font=("Arial", 12))
        self.silence_level_entry.insert(0, dotenv_values().get("SILENCE_LEVEL", "-35"))
        self.silence_level_entry.grid(column=1, row=3, padx=10, pady=5)

        ttk.Label(self, text="Minimum Interval Duration:").grid(column=0, row=4, sticky="w", padx=10, pady=5)
        self.silence_gap_entry = ttk.Entry(self, font=("Arial", 12))
        self.silence_gap_entry.insert(0, dotenv_values().get("SILENCE_GAP", "0.05"))
        self.silence_gap_entry.grid(column=1, row=4, padx=10, pady=5)

        tttr = str(DISTANCE_THRESHOLD['SHORT']) + "|" + str(DISTANCE_THRESHOLD['STRETCH'])

        ttk.Label(self, text="DISTANCE_THRESHOLD (short|stretch): ").grid(column=0, row=5, sticky="w", padx=10, pady=5)
        self.distance_threshold_entry = ttk.Entry(self, font=("Arial", 12))
        self.distance_threshold_entry.insert(0, tttr)
        self.distance_threshold_entry.grid(column=1, row=5, padx=10, pady=5)

        ttk.Button(self, text="Process Video", command=self.process_video).grid(column=1, row=7, padx=10, pady=10)
        ttk.Button(self, text="Setup Package", command=self.process_video).grid(column=2, row=7, padx=10, pady=10)
        ensure_env_file_exists()  # Ensure that .env file exists before loading
        self.title("Video Processor")
        self.geometry("700x400")
        load_dotenv()  # Load environment variables

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.*")])
        self.file_path_entry.delete(0, tk.END)
        self.file_path_entry.insert(0, file_path)
    
    def adjust_start_times(self, timestamps, gap=0.05):
        # Adjust start times with respect to previous end time or by subtracting 0.05 seconds, ensuring it does not exceed the boundaries
        for i in range(len(timestamps)):
            if i == 0:
                # If adjusting makes it negative, set start to 0
                timestamps[i]['start'] = max(timestamps[i]['start'] - gap, 0)
            else:
                # If adjusting causes overlap, set start to the previous end; otherwise, subtract gap
                if timestamps[i]['start'] - gap < timestamps[i-1]['end']:
                    timestamps[i]['start'] = timestamps[i-1]['end']
                else:
                    timestamps[i]['start'] = max(timestamps[i]['start'] - gap, timestamps[i-1]['end'])
        return timestamps

    def adjust_end_times(self, timestamps, gap=0.05):
        # Adjust end times considering not to exceed the start of the next speaking period
        for i in range(len(timestamps)-1):
            if timestamps[i+1]['start'] - timestamps[i]['end'] < gap:
                timestamps[i]['end'] = timestamps[i+1]['start']
            else:
                # Here we add gap but ensure it does not exceed the next start time
                timestamps[i]['end'] = min(timestamps[i]['end'] + gap, timestamps[i+1]['start'])
        # For the last item, add gap to the end without needing to check the next item
        if timestamps:  # Ensure list is not empty
            timestamps[-1]['end'] += gap  # Assuming there's no upper limit constraint for the last end
        return timestamps

    def adjust_timestamps(self, timestamps, gap):
        # First adjust the start times then adjust the end times
        timestamps = self.adjust_start_times(timestamps)
        timestamps = self.adjust_end_times(timestamps)
        return timestamps
        
    def splitter(self, path):
        length = get_video_length(path)
        if length > SPLIT_DISTANCE:
            segment_files, output_paths = split_video(path)
            param_list = []
            for index, (segment_file, output_path) in enumerate(zip(segment_files, output_paths)):
                param_list.append((segment_file, self.speed_entry.get(), self.silence_level_entry.get(), output_path))
            process_videos(param_list, self.thread_num_entry.get())
            printer('combine videos')
            combine_videos(output_paths, path.replace('.mp4', '_NODEADAIR.mp4'))
            for file in output_paths:
                os.remove(file)
        else:
            print('not long enough to split')
            handle_unsilence(path, self.speed_entry.get(), self.silence_level_entry.get(), path.replace('.mp4', '_output.mp4'))

    def process_video(self):
        global DISTANCE_THRESHOLD
        # Save the current environment states when the processing starts
        set_key(".env", "SPEED", self.speed_entry.get())
        set_key(".env", "FILE_PATH", self.file_path_entry.get())
        set_key(".env", "THREADS", self.thread_num_entry.get())
        set_key(".env", "SILENCE_LEVEL", self.silence_level_entry.get())
        set_key(".env", "SILENCE_GAP", self.silence_gap_entry.get())
        gap = self.silence_gap_entry.get()
        temp_folder = os.getcwd() + "\\temp"
        inputfile = self.file_path_entry.get()
        times = detectSilences.detect_silence_vad(inputfile)
        times = self.adjust_timestamps(times, (float(gap)))
        ext = inputfile.split('.')[-1]
        fffmpHandler.clip_video(inputfile, inputfile.replace(f'.{ext}', f'_nodeadair.{ext}'), times)
        # Cleanup temporary files
        print('finished')


def string_for_unsilence_function():

    return


if __name__ == "__main__":
    app = VideoProcessorApp()
    app.mainloop()
