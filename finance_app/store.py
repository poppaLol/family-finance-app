from grm_rs import GraphSession

from finance_app.models import StatementLine


class FinanceStore:
    statement_line_model = "StatementLine"

    def __init__(self, graph: GraphSession) -> None:
        self.graph = graph
        ## if we have nothing then create the schema
        if not self.graph.model_list():
            self._create_schema()

    def _create_schema(self) -> None:
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

    def list_statement_lines(self):
        return self.graph.node_find(self.statement_line_model)

    def get_statement_line(self, statement_line_id: int):
        matches = self.graph.node_find(
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
