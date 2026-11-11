# General and project-aware offline assistant
The assistant should support open-ended conversation, project architecture/setup questions, catalog queries and uploaded content in one chat. Preserve CPU-only local models and existing offline behavior.

Keep the existing local general conversation model and SQL/document/vision routes. Add a small allowlisted project knowledge module using a maintained project guide and safe runtime facts from config. This avoids cloud dependencies and inventing project details. Match explicit app/project questions and their short contextual follow-ups; catalog record/count/comparison requests and uploaded-content requests retain their existing routes.

Project answers cite real guide/config filenames and must not claim access to secrets, current counts or live internet. Do not load .env, arbitrary filesystem files, source CSV contents or credentials into the model. If Ollama is unavailable, project setup facts remain available as a sourced local summary. Preserve recent session history, English/Hindi/Hinglish behavior, PD Comparison Studio and image chat.

Validate project-vs-general-vs-data routing, project follow-ups, safe context, model fallback and existing regressions. Run live general and project questions against the restarted app.
