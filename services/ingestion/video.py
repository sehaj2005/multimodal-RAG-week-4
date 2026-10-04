from pathlib import Path
from tempfile import TemporaryDirectory
from services.config import MAX_MEDIA_SECONDS
from services.ingestion.audio import extract_audio

def extract_video(path):
    """Send only the extracted mono audio to Whisper, never the video binary."""
    from moviepy import VideoFileClip
    with VideoFileClip(str(path)) as clip:
        if clip.duration > MAX_MEDIA_SECONDS:
            raise ValueError(f'Video exceeds the {MAX_MEDIA_SECONDS}-second duration limit')
        if clip.audio is None:
            raise ValueError('This video has no audio track; upload a narrated video')
        with TemporaryDirectory(prefix='rag-video-') as directory:
            audio_path = Path(directory) / 'audio.wav'
            clip.audio.write_audiofile(str(audio_path), fps=16000, nbytes=2,
                                       codec='pcm_s16le', ffmpeg_params=['-ac', '1'], logger=None)
            return extract_audio(audio_path)
