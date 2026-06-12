import os
from grm_rs import Neo4jSession
from finance_app.store import FinanceStore


def main():
    print("Hello from famfin-tutorial!")

    graph = Neo4jSession(
        uri=os.environ["NEO4J_URI"],
        user=os.environ["NEO4J_USER"],
        password=os.environ["NEO4J_PASSWORD"],
    )

    store = FinanceStore(graph)

    print(f"Connected to store! {store}")


if __name__ == "__main__":
    main()
