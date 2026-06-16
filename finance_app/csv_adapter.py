import csv
import io
import re

from finance_app.models import StatementLine


def _normalise_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _header_index(headers: list[str], *names: str) -> int:
    normalised = [_normalise_header(header) for header in headers]
    for name in names:
        candidate = _normalise_header(name)
        if candidate in normalised:
            return normalised.index(candidate)
    expected = " or ".join(names)
    raise ValueError(f"CSV must contain a {expected} column")


def _cell(row: list[str], index: int) -> str:
    if index >= len(row):
        return ""
    return row[index].strip()


def _parse_float(value: str, row_number: int, field_name: str) -> float:
    cleaned = value.replace("£", "").replace(",", "").replace("+", "").strip()
    if not cleaned:
        raise ValueError(f"CSV row {row_number} has no {field_name} value")
    try:
        return float(cleaned)
    except ValueError as exc:
        raise ValueError(
            f"CSV row {row_number} has invalid {field_name} value {value!r}"
        ) from exc


def parse_statement_csv(content: bytes) -> list[StatementLine]:
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    headers = next(reader, None)
    if not headers:
        raise ValueError("CSV is empty")

    date_index = _header_index(headers, "date")
    counter_party_index = _header_index(headers, "counter party", "description")
    reference_index = _header_index(headers, "reference")
    transaction_type_index = _header_index(headers, "type", "transaction type")
    amount_index = _header_index(headers, "amount", "amount gbp")
    balance_index = _header_index(headers, "balance", "balance gbp")
    category_index = _header_index(
        headers,
        "spending category",
        "external category",
        "category",
    )

    lines: list[StatementLine] = []
    for row_number, row in enumerate(reader, start=2):
        if not row or all(not cell.strip() for cell in row):
            continue

        lines.append(
            StatementLine(
                date=_cell(row, date_index),
                counter_party=_cell(row, counter_party_index),
                reference=_cell(row, reference_index),
                transaction_type=_cell(row, transaction_type_index),
                amount=_parse_float(_cell(row, amount_index), row_number, "amount"),
                balance=_parse_float(_cell(row, balance_index), row_number, "balance"),
                external_category=_cell(row, category_index),
            )
        )

    if not lines:
        raise ValueError("CSV contains no statement lines")
    return lines
