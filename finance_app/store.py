from grm_rs import GraphSession

from finance_app.models import Person, PersonOwnsStatementLine, StatementLine


class FinanceStore:
    person_model = "Person"
    statement_line_model = "StatementLine"
    owns_link = "OWNS"

    def __init__(self, graph: GraphSession) -> None:
        self.graph = graph
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        model_names = {model["name"] for model in self.graph.model_list()}
        if self.statement_line_model not in model_names:
            self._create_statement_line_schema()
        if self.person_model not in model_names:
            self.graph.model_create(Person)

        link_names = {link["name"] for link in self.graph.link_list()}
        if self.owns_link not in link_names:
            self.graph.link_create(PersonOwnsStatementLine)

    def _create_statement_line_schema(self) -> None:
        self.graph.model_create(
            "StatementLine",
            "statementLineId",
            [
                ### Date,Counter Party,Reference,Type,Amount (GBP),Balance (GBP),Spending Category
                {"name": "date", "type": "string", "required": True},
                {"name": "counter_party", "type": "string", "required": True},
                {"name": "reference", "type": "string", "required": True},
                {"name": "transaction_type", "type": "string", "required": True},
                {"name": "amount", "type": "float", "required": True},
                {"name": "balance", "type": "float", "required": True},
                {"name": "external_category", "type": "string", "required": True},
            ],
        )

    def save(self, line: StatementLine):
        return self.graph.node_create(self.statement_line_model, line.model_dump())

    def import_statement_lines(self, lines: list[StatementLine], person_id: int) -> int:
        if not lines:
            return 0
        operations = []
        for index, line in enumerate(lines):
            statement_ref = f"statement:{index}"
            operations.extend(
                [
                    {
                        "op": "node_create",
                        "args": {
                            "model": self.statement_line_model,
                            "props": line.model_dump(),
                            "ref": statement_ref,
                        },
                    },
                    {
                        "op": "edge_create",
                        "args": {
                            "model": self.owns_link,
                            "from": person_id,
                            "to": statement_ref,
                            "props": {},
                        },
                    },
                ]
            )
        self.graph.batch(operations, response="summary")
        return len(lines)

    def save_person(self, person: Person):
        return self.graph.node_create(person)

    def list_persons(self):
        return self._node_find(self.person_model)

    def get_person(self, person_id: int):
        matches = self._node_find(
            self.person_model,
            {"id": person_id},
        )
        if not matches:
            return None
        return matches[0]

    def update_person(self, person_id: int, person: Person):
        return self.graph.node_update(
            self.person_model,
            person_id,
            person.model_dump(),
        )

    def delete_person(self, person_id: int) -> None:
        for edge in self.graph.edge_find(self.owns_link, {"from": person_id}):
            self.graph.edge_delete(self.owns_link, edge["id"])
        self.graph.node_delete(self.person_model, person_id)

    def list_statement_lines(self):
        return self._node_find(self.statement_line_model)

    def list_statement_lines_with_owners(self):
        persons = {
            person["id"]: person["props"]["name"]
            for person in self.list_persons()
        }
        owner_names_by_statement_id = {}
        for edge in self.graph.edge_find(self.owns_link):
            owner_name = persons.get(edge["from"])
            if owner_name is None:
                continue
            owner_names_by_statement_id.setdefault(edge["to"], []).append(owner_name)

        return [
            {
                "statement": statement,
                "owner_names": owner_names_by_statement_id.get(statement["id"], []),
            }
            for statement in self.list_statement_lines()
        ]

    def get_statement_line(self, statement_line_id: int):
        matches = self._node_find(
            self.statement_line_model,
            {"id": statement_line_id},
        )
        if not matches:
            return None
        return matches[0]

    def update_statement_line(self, statement_line_id: int, line: StatementLine):
        return self.graph.node_update(
            self.statement_line_model,
            statement_line_id,
            line.model_dump(),
        )

    def delete_statement_line(self, statement_line_id: int) -> None:
        self.graph.node_delete(self.statement_line_model, statement_line_id)

    def _node_find(self, model_name: str, filters=None):
        native = getattr(self.graph, "_native", None)
        if native is not None:
            return native.node_find(model_name, filters)
        return self.graph.node_find(model_name, filters)
