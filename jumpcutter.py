import os
import subprocess
import datetime
import json


def seconds_to_ffmpeg_format(seconds):
    # Convert seconds into ffmpeg compatible format 'hh:mm:ss.m' with 1 decimal place
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{seconds:04.1f}"


def safe_clip_creation(input_file, start, duration, output_file):
    start = float(start)
    duration = float(duration)

    # Now, the subtraction should work as start is explicitly a float
    start_fast = max(0, start - 5)  # Ensure it does not go into negative timing

    # Construct your FFmpeg command here as before
    cmd = f"ffmpeg -ss {start_fast} -i \"{input_file}\" -t {duration} -c copy \"{output_file}\""
    subprocess.run(cmd, shell=True, check=True)


def ffmpeg_concatenate(clips, output_file="final_output.mp4"):
    files = ""
    maps = ""

    # Iterate over all clips to prepare input flags and map flags
    with open("filelist.txt", "w") as f:
        for clip in clips:
            f.write(f"file '{clip}'\n")
    # Final ffmpeg command construction
    concat_cmd = f"ffmpeg -hwaccel auto -hide_banner -f concat -safe 0 -protocol_whitelist \"file,pipe,fd\" -i filelist.txt  -map \"0:0\" \"-c:0\" copy \"-disposition:0\" default -map \"0:1\" \"-c:1\" copy \"-disposition:1\" default -movflags \"+faststart\" -default_mode infer_no_subs -ignore_unknown -strict experimental -f mp4  -y  {output_file}"
    subprocess.run(concat_cmd, shell=True, check=True)

    # Cleanup the temporary file
    os.remove("filelist.txt")


def clip_and_crossfade(input_file, times, output_dir="temp"):
    import shutil
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    else:
        shutil.move(output_dir, output_dir + "old")
        os.mkdir(output_dir)
        shutil.rmtree(output_dir + "old")
    clips = []
    for i, time in enumerate(times):
        start_seconds = time['start']
        end_seconds = time['end']
        duration_seconds = time['duration']

        output_file_path = os.path.join(output_dir, f"clip_{i+1:03}.mp4")
        safe_clip_creation(input_file, start_seconds, duration_seconds, output_file_path)
        clips.append(output_file_path)

    return clips

def clean_up(dir_path):
    for file_name in os.listdir(dir_path):
        file_path = os.path.join(dir_path, file_name)
        os.remove(file_path)
    os.rmdir(dir_path)


def get_keyframe_times(video_file):
    # Use ffprobe to get keyframe timestamps
    cmd = [
        'ffprobe', '-loglevel', 'error', '-select_streams', 'v', '-skip_frame', 'nokey',
        '-show_entries', 'frame=pkt_pts_time', '-of', 'json', video_file
    ]
    # Execute command
    result = subprocess.run(cmd, capture_output=True, text=True)
    # Parse JSON output
    frames = json.loads(result.stdout)['frames']

    # Filter out frames that don't have the 'pkt_pts_time' key
    keyframe_times = []
    for frame in frames:
        if 'pkt_pts_time' in frame:
            keyframe_times.append(float(frame['pkt_pts_time']))
    return keyframe_times


def adjust_timestamps(talking_times):
    if not talking_times:
        return []
    # Ensure the list is sorted by start times
    talking_times = sorted(talking_times, key=lambda x: x['start'])

    # Adjust each talking time to offer a small buffer without causing overlaps
    for i in range(len(talking_times) - 1):
        current_talk = talking_times[i]
        next_talk = talking_times[i + 1]

        # Now, ensure there's absolutely no overlap by making end times strictly less than the next start time
        gap = next_talk['start'] - current_talk['end']
        if gap < 0.1:  # Example threshold (100 ms); adjust based on precise requirements
            mid_point = current_talk['end'] + gap / 2
            current_talk['end'] = max(current_talk['start'], mid_point - 0.05)
            next_talk['start'] = min(next_talk['end'], mid_point + 0.05)
        else:
            # Here, the gap is sufficient to not require adjustment for overlap,
            # but could adjust for aesthetics or readability
            current_talk['end'] -= 0.05  # Slightly adjust to prevent potential overlap

    # Last item, ensure it does not inadvertently overlap due to global adjustments
    last_talk = talking_times[-1]
    last_talk['start'] = max(last_talk['start'] - 0.05, 0)
    last_talk['end'] = last_talk['end'] + 0.05  # minor adjustment

    return talking_times


def combine_speaking_timestamps(speaking_intervals):
    # Ensure speaking_intervals isn't empty
    if not speaking_intervals:
        return []
    speaking_intervals = adjust_timestamps(speaking_intervals)
    # Combine speaking intervals if the gap between them is less than 0.15 seconds
    combined_intervals = []

    # Initialize the first interval with calculated duration
    temp_interval = speaking_intervals[0].copy()  # Make a copy to avoid mutating the original
    temp_interval['duration'] = temp_interval['end'] - temp_interval['start']

    for interval in speaking_intervals[1:]:
        # Ensure this interval has a 'duration' (not strictly necessary if all intervals are pre-processed)
        interval['duration'] = interval['end'] - interval['start']

        if interval['start'] - temp_interval['end'] < 0.15:
            # If the next interval is within 0.15 seconds of the current, combine them
            temp_interval['end'] = interval['end']
            temp_interval['duration'] = temp_interval['end'] - temp_interval['start']
        else:
            # If the next interval is not within the range, save the current and start a new one
            combined_intervals.append(temp_interval)
            temp_interval = interval.copy()  # Use a fresh copy for the next interval
            temp_interval['duration'] = temp_interval['end'] - temp_interval['start']

    # Don't forget to append the last processed interval
    combined_intervals.append(temp_interval)
    return combined_intervals


def adjust_intervals_with_keyframes(intervals, keyframes):
    adjusted_intervals = []
    for i, interval in enumerate(intervals):
        # Find the nearest next keyframe after each 'end'
        next_keyframe_list = [kf for kf in keyframes if kf > interval['end']]
        if next_keyframe_list:
            next_keyframe = next_keyframe_list[0]
            # Prevent adjusting the current interval's end past the next interval's start
            if i + 1 < len(intervals) and next_keyframe >= intervals[i + 1]['start']:
                # If the next keyframe is beyond the start of the next interval, do not extend to it
                adjusted_intervals.append(interval)
            else:
                # Extend the current interval’s end to the next keyframe
                adjusted_intervals.append({'start': interval['start'], 'end': next_keyframe})
        else:
            adjusted_intervals.append(interval)

    return adjusted_intervals

def get_frame_rate(video_path):
    """
    # Uses ffprobe to get the frame rate of the given video file.
    """
    ffprobe_cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    try:
        result = subprocess.run(ffprobe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        # The output is expected to be a fraction like "30/1" or "30000/1001"
        frame_rate_str = result.stdout.strip()
        # Convert the fraction to a decimal
        numerator, denominator = map(int, frame_rate_str.split('/'))
        frame_rate = numerator / denominator
        return frame_rate
    except subprocess.CalledProcessError as e:
        print(f"Failed to get frame rate due to an error: {e}")
        return None


def calculate_frame_number(time_in_seconds, frame_rate):
    """
    # Helper function to calculate the frame number from time in seconds.
    """
    return int(time_in_seconds * frame_rate)


def extract_frames_auto_frame_rate(video_path, time_segments):
    """
    # Extracts frames based on time segments, automatically determining the frame rate.
    """
    frame_rate = get_frame_rate(video_path)
    if frame_rate is not None:
        extract_frames_with_frame_numbers(video_path, time_segments, frame_rate=frame_rate)
    else:
        print("Unable to determine the video's frame rate.")
        
def extract_frames_with_frame_numbers(video_path, time_segments):
    """
    # Extracts frames from a video based on frame numbers calculated from time segments.
    """
    # Convert time segments to frame number segments

    # Construct the ffmpeg select filter expression for frame numbers
    select_expr = '+'.join([f"between(t,{seg['start']},{seg['end']})" for seg in time_segments])
    vf_expr = f"select='{select_expr}',setpts=N/FRAME_RATE/TB"
    af_expr = f"aselect='{select_expr}',asetpts=N/SR/TB"

    output_file = video_path + "_new.mp4"

    # Construct and execute the ffmpeg command
    ffmpeg_cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vf", vf_expr,
        "-af", af_expr,
        '-y',
        output_file
    ]

    try:
        result = subprocess.run(ffmpeg_cmd, shell=True, check=True)
        print(f"Output file created: {output_file} {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to extract frames due to an error: {e}")

if __name__ == "__main__":
    times = [
        {"start": 5.10, "end": 7.0},
        {"start": 11.10, "end": 15.0},
        {"start": 25.10, "end": 30.0},
        {"start": 35.100, "end": 40.0},
        {"start": 60.0, "end": 80.0}
    ]

    input_video = r"C:\Users\dower\Videos\2024-10-04_04-12-08.mp4"  # Path to the input video
    temp_folder = "temp"
    extract_frames_with_frame_numbers(input_video, times)
    print('done')
