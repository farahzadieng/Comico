# UV GUIDE FOR GROUPS

```bash
uv add --group panel
uv sync --group panel
uv sync --all-groups
uv run --group pipe1 python your_entry_point.py
```

# ENVIROMENTS

**Panel Detection** group name is `panel`

# 01 - Panel Detection

you need `config.json`, and you may use `01-Panel-Detection/config.example.json` as the example. It locates the input directory.

Model is not downloaded , use backup version and save to `01-Panel-Detection/models/best.pt`

you may place `config.json` in the root directory of the project.

```bash
uv run --group panel python Panel-Detection.py config.json
```

**The output would be loaded inside the comic directory in:** `panels.json`

## Error Handling

In case of getting error with `best.pt` download it from huggingface with :

```bash
uv run hf download \
  mosesb/best-comic-panel-detection \
  best.pt \
  --repo-type space \
  --local-dir ./01-Panel-Detection/models
```
