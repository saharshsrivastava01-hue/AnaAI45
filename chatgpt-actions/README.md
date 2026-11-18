# Connect ChatGPT to the NEXUS Movie Renderer

This repository now includes a ChatGPT Actions OpenAPI schema and a GitHub Actions render workflow.

## What this integration does

1. ChatGPT calls GitHub's workflow-dispatch API.
2. GitHub Actions checks out this repository and runs the selected procedural renderer on a GitHub-hosted Linux runner.
3. FFmpeg encodes the rendered frames into MP4.
4. The workflow uploads the MP4 and render manifest as a GitHub Actions artifact.
5. ChatGPT can inspect workflow runs and artifact metadata. Downloading the artifact still requires a valid GitHub-authenticated download flow.

The renderer currently available for the assassin_stealth profile is an original procedural CPU renderer. The NEXUS virtual GPU/TPU and RTL models are not physical accelerators and are not automatically executing the film shader today. GitHub-hosted runners provide the actual compute.

## Configure a ChatGPT Action

1. Create or edit a custom GPT that supports Actions.
2. Add the OpenAPI schema from chatgpt-actions/nexus-movie-renderer-openapi.yaml.
3. Set Action authentication to API Key, auth type Bearer.
4. Create a fine-grained GitHub personal access token restricted to this repository. Grant Actions: Read and write and Contents: Read-only. Do not paste the token into a chat or commit it to this repository.
5. Save the Action.

Then ask the configured GPT: "Start a NEXUS assassin stealth render, 120 frames, 12 fps, 180 by 320."

The Action should call startNexusMovieRender, then getNexusRenderRuns to inspect the run. A successful dispatch returns HTTP 204; that only means GitHub accepted the request. Wait for the run conclusion to be success, then call getNexusRenderArtifacts using the run ID.

## Render profiles and safe bounds

- assassin_stealth: 120-frame original rooftop stealth sequence by default.
- procedural_demo: existing NEXUS procedural ray-render demo.
- Frames: 24–360; FPS: 1–60; width and height: 32–640.
- GitHub artifact retention: 7 days.

This is an automated software rendering pipeline, not a trillion-times-faster GPU or a physical 4D cinema system. No external AI video generation API is used.
