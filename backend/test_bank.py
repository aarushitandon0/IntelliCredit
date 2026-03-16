import sys
sys.path.insert(0, ".")
from src.ingestion.bank_parser import parse_bank_statement

result = parse_bank_statement("../data/mock_bank/bank_statement_5yr.csv")
print(result["circular_trading"])
print(result["risk_flags"])