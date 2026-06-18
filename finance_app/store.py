from typing import cast

from grm_rs import GraphSession

from finance_app.csv_adapter import normalise_statement_key
from finance_app.models import (
    Category,
    Person,
    PersonOwnsStatementLine,
    Rule,
    RuleAssignsCategory,
    StatementLine,
    StatementLineCategorisedAs,
)


class FinanceStore:
    category_model = "Category"
    person_model = "Person"
    rule_model = "Rule"
    statement_line_model = "StatementLine"
    categorised_as_link = "CATEGORISED_AS"
    owns_link = "OWNS"
    rule_assigns_category_link = "ASSIGNS_CATEGORY"

    def __init__(self, graph: GraphSession) -> None:
        self.graph = graph
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        model_names = {model["name"] for model in self.graph.model_list()}
        if self.statement_line_model not in model_names:
            self.graph.model_create(StatementLine)
        if self.person_model not in model_names:
            self.graph.model_create(Person)
        if self.category_model not in model_names:
            self.graph.model_create(Category)
        if self.rule_model not in model_names:
            self.graph.model_create(Rule)

        link_names = {link["name"] for link in self.graph.link_list()}
        if self.owns_link not in link_names:
            self.graph.link_create(PersonOwnsStatementLine)
        if self.categorised_as_link not in link_names:
            self.graph.link_create(StatementLineCategorisedAs)
        if self.rule_assigns_category_link not in link_names:
            self.graph.link_create(RuleAssignsCategory)

    def save(self, line: StatementLine):
        return self.graph.node_create(self.statement_line_model, line.model_dump())

    def import_statement_lines(
        self,
        lines: list[StatementLine],
        person_id: int,
        category_names_by_hash: dict[str, str] | None = None,
        rule_hashes: set[str] | None = None,
    ) -> int:
        if not lines:
            return 0
        rule_categories = self._rule_category_map()
        category_names_by_hash = category_names_by_hash or {}
        rule_hashes = rule_hashes or set()
        operations = []
        for index, line in enumerate(lines):
            statement_ref = f"statement:{index}"
            key = normalise_statement_key(line)
            category_name = category_names_by_hash.get(line.source_hash, "").strip()
            if category_name:
                category_id = self.save_category(Category(name=category_name))["id"]
                method = "manual_rule" if line.source_hash in rule_hashes else "manual"
                if line.source_hash in rule_hashes:
                    self.save_rule_for_line(line, category_id)
            else:
                category_id = rule_categories.get(key)
                method = "rule"
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
            if category_id is not None:
                operations.append(
                    {
                        "op": "edge_create",
                        "args": {
                            "model": self.categorised_as_link,
                            "from": statement_ref,
                            "to": category_id,
                            "props": {"method": method},
                        },
                    }
                )
        self.graph.batch(operations, response="summary")
        return len(lines)

    def save_category(self, category: Category):
        existing = self.get_category_by_name(category.name)
        if existing is not None:
            return existing
        return self.graph.node_create(category)

    def list_categories(self):
        return sorted(
            self._node_find(self.category_model),
            key=lambda category: cast(str, category["props"]["name"]).lower(),
        )

    def get_category(self, category_id: int):
        matches = self._node_find(self.category_model, {"id": category_id})
        if not matches:
            return None
        return matches[0]

    def get_category_by_name(self, name: str):
        matches = self._node_find(self.category_model, {"name": name})
        if not matches:
            return None
        return matches[0]

    def update_category(self, category_id: int, category: Category):
        return self.graph.node_update(
            self.category_model,
            category_id,
            category.model_dump(),
        )

    def delete_category(self, category_id: int) -> None:
        for link_name in (self.categorised_as_link, self.rule_assigns_category_link):
            for edge in self.graph.edge_find(link_name, {"to": category_id}):
                self.graph.edge_delete(link_name, edge["id"])
        self.graph.node_delete(self.category_model, category_id)

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
        categories = {
            category["id"]: category["props"]["name"]
            for category in self.list_categories()
        }
        owner_names_by_statement_id = {}
        for edge in self.graph.edge_find(self.owns_link):
            owner_name = persons.get(edge["from"])
            if owner_name is None:
                continue
            owner_names_by_statement_id.setdefault(edge["to"], []).append(owner_name)

        category_names_by_statement_id = {}
        for edge in self.graph.edge_find(self.categorised_as_link):
            category_name = categories.get(edge["to"])
            if category_name is None:
                continue
            category_names_by_statement_id.setdefault(edge["from"], []).append(
                category_name
            )

        return [
            {
                "statement": statement,
                "owner_names": owner_names_by_statement_id.get(statement["id"], []),
                "category_names": category_names_by_statement_id.get(
                    statement["id"], []
                ),
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
        for link_name in (self.owns_link, self.categorised_as_link):
            for edge in self.graph.edge_find(link_name, {"from": statement_line_id}):
                self.graph.edge_delete(link_name, edge["id"])
            for edge in self.graph.edge_find(link_name, {"to": statement_line_id}):
                self.graph.edge_delete(link_name, edge["id"])
        self.graph.node_delete(self.statement_line_model, statement_line_id)

    def categorise_statement_line(
        self,
        statement_line_id: int,
        category_name: str,
        create_rule: bool,
    ) -> None:
        statement = self.get_statement_line(statement_line_id)
        if statement is None:
            return
        category = self.save_category(Category(name=category_name.strip()))
        self._replace_statement_category(
            statement_line_id,
            category["id"],
            "manual_rule" if create_rule else "manual",
        )
        if create_rule:
            self.save_rule_for_statement(statement, category["id"])

    def save_rule_for_statement(self, statement, category_id: int) -> None:
        key = normalise_statement_key(
            StatementLine.model_validate(statement["props"])
        )
        self._save_rule(key, category_id)

    def save_rule_for_line(self, line: StatementLine, category_id: int) -> None:
        self._save_rule(normalise_statement_key(line), category_id)

    def category_for_statement_line(self, line: StatementLine):
        category_id = self._rule_category_map().get(normalise_statement_key(line))
        if category_id is None:
            return None
        return self.get_category(category_id)

    def _save_rule(self, key: str, category_id: int) -> None:
        existing = self._node_find(self.rule_model, {"key": key})
        if existing:
            rule_id = existing[0]["id"]
            self.graph.node_update(
                self.rule_model,
                rule_id,
                Rule(key=key, rule_type="single").model_dump(),
            )
            for edge in self.graph.edge_find(
                self.rule_assigns_category_link,
                {"from": rule_id},
            ):
                self.graph.edge_delete(self.rule_assigns_category_link, edge["id"])
        else:
            rule_id = self.graph.node_create(
                Rule(key=key, rule_type="single")
            )["id"]

        self.graph.edge_create(
            self.rule_assigns_category_link,
            rule_id,
            category_id,
            {"percent": 1.0},
        )

    def apply_rules_to_uncategorised_statement_lines(self) -> int:
        rule_categories = self._rule_category_map()
        if not rule_categories:
            return 0

        categorised_statement_ids = {
            edge["from"]
            for edge in self.graph.edge_find(self.categorised_as_link)
        }
        count = 0
        for statement in self.list_statement_lines():
            if statement["id"] in categorised_statement_ids:
                continue
            key = normalise_statement_key(
                StatementLine.model_validate(statement["props"])
            )
            category_id = rule_categories.get(key)
            if category_id is None:
                continue
            self._replace_statement_category(statement["id"], category_id, "rule")
            count += 1
        return count

    def _replace_statement_category(
        self,
        statement_line_id: int,
        category_id: int,
        method: str,
    ) -> None:
        for edge in self.graph.edge_find(
            self.categorised_as_link,
            {"from": statement_line_id},
        ):
            self.graph.edge_delete(self.categorised_as_link, edge["id"])
        self.graph.edge_create(
            self.categorised_as_link,
            statement_line_id,
            category_id,
            {"method": method},
        )

    def _rule_category_map(self) -> dict[str, int]:
        rules: dict[int, str] = {
            rule["id"]: cast(str, rule["props"]["key"])
            for rule in self._node_find(self.rule_model)
            if rule["props"].get("rule_type") == "single"
        }
        return {
            rule_key: edge["to"]
            for edge in self.graph.edge_find(self.rule_assigns_category_link)
            if (rule_key := rules.get(edge["from"])) is not None
        }

    def _node_find(self, model_name: str, filters=None):
        native = getattr(self.graph, "_native", None)
        if native is not None:
            return native.node_find(model_name, filters)
        return self.graph.node_find(model_name, filters)
