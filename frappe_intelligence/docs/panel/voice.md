# Voice input

A microphone between the paperclip and **Send** (approved board 3c). The recording is turned into text **on this server** with Whisper, never by a browser or cloud speech service, and the text goes into the box: the user checks it and sends.

```
[🎤] click → the browser asks for the microphone → recording (red square: click to stop)
     → upload as a private File → api.voice.transcribe → background job (utils/background.py)
     → documents/voice.transcribe_recording: Whisper → text; the recording is deleted
     → fi_job event → the text is added to the box
```

| Part | Detail |
|---|---|
| When it shows | Only when the `voice` extra (`faster-whisper`) is installed ([../DEPLOYMENT.md](../DEPLOYMENT.md#optional-packages)) |
| Language | **AI Settings → Chat → Voice Transcription Language** (e.g. `ar`); empty means the language spoken. The button's label names it: "Voice input (ar)" |
| Formats | Whatever the browser records (WebM/Opus, Ogg, MP4); Whisper reads them all |
| Model | `whisper_model_size` in site_config.json (default `medium`); the first use downloads and loads it, which takes a while |
| Errors | No HTTPS, microphone blocked, or a failed transcription show a red alert; the box keeps what was typed |

## Security

| Risk | Guard |
|---|---|
| Transcribing or deleting another file | Only an audio file the user just uploaded is accepted (their own, private, attached to nothing), since it is deleted afterwards |
| Recordings piling up | The recording is deleted after transcription, also when it fails |
| Cost | Frappe rate limit on `transcribe` (20 a minute per user) |
