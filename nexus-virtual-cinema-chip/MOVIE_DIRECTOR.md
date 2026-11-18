# NEXUS Movie Director — offline pre-production

Run from this directory:

```bash
python nexus_movie_director.py --title "NEXUS: The Signal" --genre sci-fi --duration 30 --platform youtube-shorts --out NEXUS_MOVIE_PROJECT
```

It creates:
- `production_plan.json`: timed story beats, director notes, edit and retention guidance.
- `shot_prompts.txt`: prompts/directions to use with a separately selected image/video generator or a human artist.
- `captions.srt`: timed subtitle file.

Supported genres: sci-fi, adventure, fantasy, sports.
Supported platforms: YouTube Shorts, Instagram Reels, TikTok.
Duration: 15–90 seconds.

This is a deterministic offline planning tool, not a generative AI model. It does
not create photorealistic AI video, upload content, predict recommendation
algorithms, or guarantee views/virality. The current NEXUS renderer generates
procedural CPU-rendered frames of its existing scene; it is not yet wired to
these story prompts. The next step is to connect shot plans to controllable
scene assets and a real video-generation/render backend.
