import csv
import hashlib
import io
import json
import re

from finance_app.models import StatementLine


def normalise_statement_key(line: StatementLine) -> str:
    text = line.counter_party.upper()
    for noise in (
        "GOOGLE PAY",
        "APPLE PAY",
        "CARD PAYMENT",
        "CARD PURCHASE",
        "CONTACTLESS",
        "VISA",
        "MASTERCARD",
        "DEBIT",
        "CREDIT",
        "POS",
        "ONLINE",
    ):
        text = text.replace(noise, " ")

    text = re.sub(r"\b\d{3,}\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or "UNKNOWN"


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


def _statement_hash(source_name: str, row_number: int, props: dict[str, object]) -> str:
    payload = {
        "source_name": source_name,
        "row_number": row_number,
        "statement_line": props,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def parse_statement_csv(content: bytes, source_name: str = "") -> list[StatementLine]:
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

        props = {
            "date": _cell(row, date_index),
            "counter_party": _cell(row, counter_party_index),
            "reference": _cell(row, reference_index),
            "transaction_type": _cell(row, transaction_type_index),
            "amount": _parse_float(_cell(row, amount_index), row_number, "amount"),
            "balance": _parse_float(_cell(row, balance_index), row_number, "balance"),
            "external_category": _cell(row, category_index),
        }

        lines.append(
            StatementLine(
                source_hash=_statement_hash(source_name, row_number, props),
                **props,
            )
        )

    if not lines:
        raise ValueError("CSV contains no statement lines")
    return lines
