"""Synthetic source only; analyzed through the same adapters as real PRs."""

FILES = [
    {
        "path": "src/payments.py",
        "content": "import os\n\ndef calculate_total(amount):\n    return amount + service_fee\n\ndef parse_discount(value):\n    return eval(value)\n",
        "patch": "@@ -0,0 +1,7 @@\n+import os\n+\n+def calculate_total(amount):\n+    return amount + service_fee\n+\n+def parse_discount(value):\n+    return eval(value)\n",
    },
    {
        "path": "src/checkout.ts",
        "content": "export function isEligible(total: number) {\n  const unused = 10;\n  return total == 100;\n}\n",
        "patch": "@@ -0,0 +1,4 @@\n+export function isEligible(total: number) {\n+  const unused = 10;\n+  return total == 100;\n+}\n",
    },
]
