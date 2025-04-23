from cpu.alu import ALU

def test_add():
    assert ALU.execute("ADD", 2, 3) == 5

def test_div_floor():
    assert ALU.execute("DIV", 7, 3) == 2
