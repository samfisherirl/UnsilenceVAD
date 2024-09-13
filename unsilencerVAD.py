from unsilence import Unsilence
from unsilence.lib.detect_silence.DetectSilence import convert_video_to_audio
from pathlib import Path
import traceback
import tkinter as tk
from tkinter import ttk, filedialog
import sv_ttk
import os
from dotenv import load_dotenv, dotenv_values, set_key


def ensure_env_file_exists():
    env_path = ".env"
    if not os.path.exists(env_path):
        open(env_path, 'a').close()  # Create the .env file if it does not exist


class VideoProcessorApp(tk.Tk):
    def __init__(self):
        super().__init__()

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
        self.minimum_interval_duration_entry = ttk.Entry(self, font=("Arial", 12))
        self.minimum_interval_duration_entry.insert(0, dotenv_values().get("INTERVAL_DURATION", "0.125"))
        self.minimum_interval_duration_entry.grid(column=1, row=4, padx=10, pady=5)

        ttk.Button(self, text="Process Video", command=self.process_video).grid(column=1, row=5, padx=10, pady=10)
        ensure_env_file_exists()  # Ensure that .env file exists before loading
        self.title("Video Processor")
        self.geometry("600x300")
        load_dotenv()  # Load environment variables
        
    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.mov")])
        self.file_path_entry.delete(0, tk.END)
        self.file_path_entry.insert(0, file_path)

    def process_video(self):
        # Save the current environment states when the processing starts
        set_key(".env", "SPEED", self.speed_entry.get())
        set_key(".env", "FILE_PATH", self.file_path_entry.get())
        set_key(".env", "THREADS", self.thread_num_entry.get())
        set_key(".env", "SILENCE_LEVEL", self.silence_level_entry.get())
        set_key(".env", "INTERVAL_DURATION", self.minimum_interval_duration_entry.get())

        file_path = self.file_path_entry.get()
        speed = self.speed_entry.get()
        silence_level = self.silence_level_entry.get()
        minimum_interval_duration = self.minimum_interval_duration_entry.get()
        output_path = f"{file_path.rsplit('.', 1)[0]}_nodeadair.{file_path.split('.')[-1]}"
        command = f".\\_internal\\unsilenced.exe \"{file_path}\" \"{output_path}\" -ss {speed} -sl {silence_level} -mid {minimum_interval_duration} -y"
        
        print(f"Processed {file_path} with speed {speed}, silence level {silence_level}, and minimum interval duration {minimum_interval_duration}. Output at {output_path}")
        infile = "C:\\Users\\dower\\Downloads\\is Jake Weddle Okay-00.00.00.000-00.08.08.500.mp4"

        cwd = Path.cwd()
        u = Unsilence(file_path, cwd / ".tmp")

        u.detect_silence()
        
        estimated_time = u.estimate_time(silent_speed=int(speed))  # Estimate time savings
        print(estimated_time)


        if '.mp4' in infile:
            outf = infile.replace('.mp4', '_unsilenced.mp4')
        elif ".mov" in infile:
            outf = infile.replace('.mov', '_unsilenced.mov')

        u.render_media(f"{output_path}", silence_volume=silence_level)  # No options specified

if __name__ == "__main__":
    app = VideoProcessorApp()
    app.mainloop()
