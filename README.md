# FAMILY FINANCE TUTORIAL APPLICATION

## BASIC INSTRUCTIONS

You will need docker desktop or an available neo4j server to run this.

Have that started and ensure you have environment variables set. For example:
```
NEO4J_URI=bolt://127.0.0.1:7688
NEO4J_USER=neo4j
NEO4J_PASSWORD=change-this-password
```

1. Install `uv`
1. Clone this project
1. Clone `grm-rs` in a sibling folder
1. Build the python library with `maturin build --manifest-path grm-python/Cargo.toml --release --out dist` in the root of the folder
1. `uv sync` in this project
1. run a neo4j community docker in
1. `uv run main.py` to prove you can connect to the store

```
$ uv run main.py
Hello from famfin-tutorial!
Connected to store! <finance_app.store.FinanceStore object at 0x7bb6e8f2ea50>
```
