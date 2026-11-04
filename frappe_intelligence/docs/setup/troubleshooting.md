# Troubleshooting

| Symptom | Fix |
|---|---|
| Desk fails to boot after installing (`SessionBootFailed`) | Frappe is older than the app expects; update Frappe to a recent v16 |
| No app tile, dock buttons or sidebars | `bench --site <site> migrate`, `bench build --app frappe_intelligence`, `bench --site <site> clear-cache`, then reload; on an old v16 release, update Frappe. The user must have the Intelligence User role ([permissions.md](permissions.md)) |
| Assistant missing from the dock | Same as above; the dock's sparkles button only shows for allowed users |
| A change in the code does nothing in the panel | Restart the workers: they keep the old code (`bench restart`) |
| Answers never arrive | A worker must run the `long` queue (`bench start` or supervisor) |
| "Ollama has no model named …" | `ollama pull <model>` or `bench fi-setup-ollama`, or choose another provider in AI Settings |
| "Cannot connect to Ollama" | Start it (`ollama serve`) or choose another provider |
| A local model is very slow, or the machine runs out of memory | A 7B model needs several GB free; use a smaller model or a cloud provider |
| Photos or scanned PDFs are not read | Install the `ocr` extra ([install.md](install.md#optional-packages)) |
| No microphone in the panel | Install the `voice` extra |
| "Too many requests" | More than 20 calls a minute to one endpoint; wait, or change `REQUESTS_PER_MINUTE` in `utils/access.py` |
| Replies in the wrong language | Set AI Settings → Response Language ([settings.md](settings.md#chat)) |
| A post-processor does not run | Check that a worker runs the `default` queue, and the Error Log for an unsafe callback |
| A user cannot use the assistant | Give them the Intelligence User role; Administrator too, on its own User form |
| "Agent" is greyed out in the mode menu | Its note says why: turn on Allow Agent Mode in AI Settings, or give the user the Intelligence Agent role |
