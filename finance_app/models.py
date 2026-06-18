from typing import ClassVar

from pydantic import BaseModel


class Person(BaseModel):
    __grm_id_field__: ClassVar[str] = "personId"

    name: str


class Category(BaseModel):
    __grm_id_field__: ClassVar[str] = "categoryId"

    name: str


class Rule(BaseModel):
    __grm_id_field__: ClassVar[str] = "ruleId"

    key: str
    rule_type: str


## from statements we might want to support the following kinds of input
## Date,Counter Party,Reference,Type,Amount (GBP),Balance (GBP),Spending Category
class StatementLine(BaseModel):
    __grm_id_field__: ClassVar[str] = "statementLineId"

    source_hash: str = ""
    date: str
    counter_party: str
    reference: str
    transaction_type: str
    amount: float
    balance: float
    external_category: str


class PersonOwnsStatementLine(BaseModel):
    __grm_link_name__: ClassVar[str] = "OWNS"
    __grm_from_model__: ClassVar[str] = "Person"
    __grm_to_model__: ClassVar[str] = "StatementLine"
    __grm_id_field__: ClassVar[str] = "ownsId"
    __grm_from_id_field__: ClassVar[str] = "person_id"
    __grm_to_id_field__: ClassVar[str] = "statement_line_id"

    person_id: int
    statement_line_id: int


class StatementLineCategorisedAs(BaseModel):
    __grm_link_name__: ClassVar[str] = "CATEGORISED_AS"
    __grm_from_model__: ClassVar[str] = "StatementLine"
    __grm_to_model__: ClassVar[str] = "Category"
    __grm_id_field__: ClassVar[str] = "statementCategoryId"
    __grm_from_id_field__: ClassVar[str] = "statement_line_id"
    __grm_to_id_field__: ClassVar[str] = "category_id"

    statement_line_id: int
    category_id: int
    method: str


class RuleAssignsCategory(BaseModel):
    __grm_link_name__: ClassVar[str] = "ASSIGNS_CATEGORY"
    __grm_from_model__: ClassVar[str] = "Rule"
    __grm_to_model__: ClassVar[str] = "Category"
    __grm_id_field__: ClassVar[str] = "ruleCategoryId"
    __grm_from_id_field__: ClassVar[str] = "rule_id"
    __grm_to_id_field__: ClassVar[str] = "category_id"

    rule_id: int
    category_id: int
    percent: float
