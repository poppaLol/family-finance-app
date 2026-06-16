from typing import ClassVar

from pydantic import BaseModel


class Person(BaseModel):
    __grm_id_field__: ClassVar[str] = "personId"

    name: str


## from statements we might want to support the following kinds of input
## Date,Counter Party,Reference,Type,Amount (GBP),Balance (GBP),Spending Category
class StatementLine(BaseModel):
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
