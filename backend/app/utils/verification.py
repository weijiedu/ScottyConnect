"""
Verification code generator
"""

import random

def generate_verification_code() -> str:
    code = ""
    for _ in range(6):
        code += str(random.randint(0, 9))
    return code