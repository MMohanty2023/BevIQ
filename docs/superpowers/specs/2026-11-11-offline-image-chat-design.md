# Offline CPU image conversations

The user needs arbitrary photos, including photos containing no writing, to support detailed descriptions, poetry on request and follow-up questions. The assistant must work offline without a GPU and remain deployable.

## Approaches
Cloud vision was considered for speed but conflicts with the user's offline requirement. OCR alone reads writing and cannot describe scenes. Use local Ollama qwen3-vl:2b-instruct for image questions, keeping llama3.2 for ordinary chat and catalog retrieval. Model choice is an implementation recommendation, not a speed guarantee.

## Behavior
Validate and normalize image uploads, persist them by conversation, and send actual image pixels to the vision model. Do not reject valid photos for missing text. Follow-ups explicitly referring to an image use that session's latest image. Ordinary questions keep their existing route. Reply in the requested language; write poetry only when requested. Keep observation separate from imaginative writing.

## CPU and deployment
Force num_gpu=0 for vision and text requests. Configure host, vision model, timeout and output limit through environment variables. No external inference services, API keys or automatic model downloads. Download model weights once during setup while connected, then inference works without internet. CPU hosts must retain model weights, images and chat storage on persistent volumes; 8 GB RAM is a starting point to validate, not a performance guarantee.

## Validation
Test text-free photos, corrupt files, oversized dimensions, per-session image ownership, actual base64 pixels and CPU request settings, image follow-ups and normal chat regressions. Report missing models, unavailable Ollama and generation failures clearly. Run a live CPU image description and poetry request and measure its duration.
