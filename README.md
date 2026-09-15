# UV GUIDE FOR GROUPS

```bash
uv add --group panel
uv sync --group pipe1
uv sync --all-groups
uv run --group pipe1 python your_entry_point.py
```

# ENVIROMENTS

**Panel Detection** group name is `panel`

# 01 - Panel Detection

you need `config.json`, and you may use `01-Panel-Detection/config.example.json` as the example. It locates the input directory.

you may place `config.json` in the root directory of the project.

```bash
uv run --group panel python Panel-Detection.py config.json
```

## Error Handling

In case of getting error with `best.pt` download it from huggingface with :

```bash
uv run hf download \
  mosesb/best-comic-panel-detection \
  best.pt \
  --repo-type space \
  --local-dir ./01-Panel-Detection/models
```
