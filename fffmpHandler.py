import subprocess
import detectSilences


def clip_video(input_file, output_file, time_ranges):
    """
    Clips sections from a video file based on provided time ranges and combines them.

    Args:
    input_file (str): Path to the input video file.
    output_file (str): Path where the output video will be saved.
    time_ranges (list of tuples): List of time ranges (start, end) in seconds for the sections to be clipped.

    Example:
    clip_video('noise_a.mp4', 'outfile_noise_a.mp4', [(0, 2.00093), (4.00009, 6.00256), (7.99961, 9.99989), (12.0001, 13.9998)])
    """
    # Generate the select and aselect filter expressions based on the time ranges
   # Build the selection expression for both video and audio streams
    select_expr = '+'.join([f"between(t,{range_dict['start']},{range_dict['end']})" for range_dict in time_ranges])
    video_filter = f"select='{select_expr}',setpts=N/FRAME_RATE/TB"
    audio_filter = f"aselect='{select_expr}',asetpts=N/SR/TB"

    # Construct the FFmpeg command
    command = [
        'ffmpeg',
        '-hwaccel', 'auto',
        '-i', input_file,
        '-vf', video_filter,
        '-af', audio_filter,
        '-y',
        output_file
    ]

    # Execute the FFmpeg command
    subprocess.run(command)


# Example usage
if __name__ == '__main__':
    inputfile = r"E:\download\kelly\2024-10-25_16-50-01_2-01.01.53.817-01.09.34.014.mp4"
    d = detectSilences.detect_silence_vad(inputfile)
    clip_video(inputfile, 'temp.mp4', d)
