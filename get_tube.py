from pytubefix import YouTube
from pytubefix.helpers import reset_cache

import os
import subprocess
import argparse
import sys
import time
from threading import Lock
from concurrent.futures import ThreadPoolExecutor

from utils import bell_ring


# Shrink mp4 file:
# ffmpeg -i input.mp4 -vcodec libx265 -crf 28 -preset medium -acodec aac -b:a 128k output.mp4
# ffmpeg -i input.mp4 -vcodec libx264 -crf 26 -preset medium -acodec aac -b:a 96k output.mp4                        - whatsapp OK
# ffmpeg -loglevel error -stats -i input.mp4 -vcodec libx264 -crf 26 -preset medium -acodec aac -b:a 96k output.mp4 - hide warnings


def ffmpeg_with_progress(video_file, audio_file, final_file, total_duration):
    """
    total_duration = duration of the final output in seconds
    """

    process = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-i", video_file,
            "-i", audio_file,
            "-c:v", "copy",
            "-map", "0:v",
            "-map", "1:a",
            "-progress", "pipe:1",
            "-nostats",
            final_file
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )

    start_time = time.time()

    for line in process.stdout:
        if "out_time_ms" in line:
            ms = int(line.split("=")[1])
            seconds = ms / 1_000_000

            # --- percentage ---
            pct = min(seconds / total_duration, 1.0)
            percent = pct * 100

            # --- speed (x realtime) ---
            elapsed = time.time() - start_time
            speed = seconds / elapsed if elapsed > 0 else 0

            # --- ETA ---
            if speed > 0:
                remaining = (total_duration - seconds) / speed
            else:
                remaining = 0

            # --- progress bar ---
            bar_len = 30
            filled = int(bar_len * pct)
            bar = "█" * filled + "░" * (bar_len - filled)

            sys.stdout.write(
                f"\r[{bar}] {percent:5.1f}%  "
                f"ETA: {remaining:5.1f}s  "
                f"Speed: {speed:4.2f}x"
            )
            sys.stdout.flush()

        if "progress=end" in line:
            break

    process.wait()
    
    print("\nFinito!")


progress = {}
lock = Lock()
reset_cache()

def on_progress(stream, chunk, bytes_remaining):
    total = stream.filesize or stream.filesize_approx
    if not total:
        return

    done = total - bytes_remaining
    pct = done / total * 100

    with lock:
        progress[f"{stream.type}-{stream.itag}"] = pct
        render_progress()


def render_progress():
    sys.stdout.write("\r")
    for itag, pct in progress.items():
        sys.stdout.write(f"[{itag}: {pct:05.2f}%] ")
    sys.stdout.flush()



def download_highest_quality_with_audio(url: str, output_path: str = ".", filename: str = "output"):
    
    os.makedirs(output_path, exist_ok=True)

    yt = YouTube(url, on_progress_callback=on_progress)

    # 1. Try progressive (video+audio in one file)
    progressive = (
        yt.streams
        .filter(progressive=True, file_extension="mp4")
        .order_by("resolution")
        .desc()
        .first()
    )

    progressive_res = int(progressive.resolution.replace("p", "")) if progressive else 0

    if progressive and progressive_res >= 720:
        print("\nDownloading progressive stream (video+audio in one file)...")
        final_path = progressive.download(output_path=output_path, filename=f"{filename}.mp4")
        return final_path
        

    print("\nNo progressive stream available. Using adaptive streams...")

    video_stream = (
        yt.streams
        .filter(adaptive=True, only_video=True, mime_type="video/mp4")
        .order_by("resolution")
        .desc()
        .first()
    )

    audio_stream = (
        yt.streams
        .filter(adaptive=True, only_audio=True, mime_type="audio/mp4")
        .order_by("abr")
        .desc()
        .first()
    )

    # print("\nDownloading video...")
    # video_file = video_stream.download(output_path=output_path, filename=f"{filename}_video.mp4")

    # print("\nDownloading audio...")
    # audio_file = audio_stream.download(output_path=output_path, filename=f"{filename}_audio.m4a")

    def download_video():
        return video_stream.download(output_path=output_path, filename=f"{filename}_video.mp4")

    def download_audio():
        return audio_stream.download(output_path=output_path, filename=f"{filename}_audio.m4a")

    with ThreadPoolExecutor(max_workers=2) as executor:
        f_video = executor.submit(download_video) 
        f_audio = executor.submit(download_audio)

        # Wait for both to finish 
        f_video.result() 
        f_audio.result()      


    video_path = os.path.join(output_path, f"{filename}_video.mp4")
    audio_path = os.path.join(output_path, f"{filename}_audio.m4a")
    final_file = os.path.join(output_path, f"{filename}.mp4")

    print("\nStiching video and audio...")
    ffmpeg_with_progress(video_path, audio_path, final_file, yt.length)


    # 3. Cleanup temp files
    print("\nCleaning up temporary files...")
    for f in [video_path]:
        try:
            os.remove(f)
        except FileNotFoundError:
            pass

    return final_file


def main():
    parser = argparse.ArgumentParser(description="Download highest‑quality YouTube video with merged audio.")
    parser.add_argument("url",                                          help="YouTube video URL")
    parser.add_argument("-f", "--filename", default="output",           help="Output filename (without extension)")
    parser.add_argument("-o", "--output",   default="myvideo",          help="Output directory")
    parser.add_argument("-l", "--logfile",  default="download_log.txt", help="Path to log file")

    args = parser.parse_args()

    final = download_highest_quality_with_audio(
        args.url,
        output_path=args.output,
        filename=args.filename
    )

    # --- Logging step ---
    os.makedirs(args.output, exist_ok=True)

    log_file = os.path.join(args.output, args.logfile)
    with open(log_file, "a", encoding="utf-8") as log: 
        log.write(args.url + " => " + args.filename + "\n") 
    
    print("Saved to:", final) 
    print(f"Logged URL to {log_file}")

    # Finito!
    bell_ring()    

if __name__ == '__main__':
    main()
    
