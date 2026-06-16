from pydantic import BaseModel


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
