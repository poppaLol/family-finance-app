# FAMILY FINANCE TUTORIAL APPLICATION

## BASIC INSTRUCTIONS

You will need docker desktop or an available neo4j server to run this.

Have that started and ensure you have environment variables set. For example:
```
export NEO4J_URI=bolt://127.0.0.1:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=change-this-password
```

1. Install `uv`
1. Clone this project
1. Clone `https://github.com/poppaLol/grm-rs` in a sibling folder
1. Build the python library with `maturin build --manifest-path grm-python/Cargo.toml --release --out dist` in the root of the folder
1. `uv sync` in this project
1. `uv run main.py` to prove you can connect to the store

```
$ uv run uvicorn main:app --reload
Hello from famfin-tutorial!
INFO:     Will watch for changes in these directories: ['/home/<USER>/source/famfin-tutorial']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [413631] using WatchFiles
INFO:     Started server process [413633]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

Navigate to the URI to see if the connection to the database succeeded.
