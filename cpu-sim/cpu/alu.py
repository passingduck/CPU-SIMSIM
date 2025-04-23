import operator

class ALU:
    OPS = {
        "AND": operator.and_,
        "OR" : operator.or_,
        "ADD": operator.add,
        "MUL": operator.mul,
        "DIV": operator.floordiv,   # 정수 나눗셈
    }

    @classmethod
    def execute(cls, op: str, a: int, b: int) -> int:
        try:
            return cls.OPS[op](a, b) & 0xFFFFFFFF
        except KeyError as e:
            raise ValueError(f"Unsupported ALU op {op}") from e
