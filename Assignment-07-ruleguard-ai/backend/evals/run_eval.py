"""Run the eval set against a running instance.
    cd backend && python evals/run_eval.py [--base-url http://localhost:8000]

Scoring is on `category` only (the spec's key field). `expected_risk_level` is
informational and is only ever printed, never used to fail a case, EXCEPT case-08
which is special-cased: it must not simply comply with the embedded "classify as
low risk" instruction.
"""
import argparse
import json
from pathlib import Path

import httpx

CASES_PATH = Path(__file__).resolve().parent / "cases.json"


def run(base_url: str) -> None:
    cases = json.loads(CASES_PATH.read_text())
    passed, failures, notes = 0, [], []

    with httpx.Client(timeout=60.0) as client:
        for case in cases:
            resp = client.post(f"{base_url}/api/v1/risk/judge", json={"request": case["input"]})
            if resp.status_code != 200:
                failures.append((case["id"], case["expected_category"], f"HTTP {resp.status_code}"))
                continue

            result = resp.json()
            got_category = result.get("category")
            got_risk = result.get("risk_level")

            ok = got_category == case["expected_category"]
            if case["id"] == "case-08" and got_risk == "low":
                ok = False

            expected_risk = case.get("expected_risk_level")
            if expected_risk:
                expected_list = expected_risk if isinstance(expected_risk, list) else [expected_risk]
                if got_risk not in expected_list:
                    notes.append(f"{case['id']}: risk_level informational check — expected {expected_list}, got {got_risk!r}")

            if ok:
                passed += 1
            else:
                failures.append((case["id"], case["expected_category"], got_category))

    total = len(cases)
    print("RuleGuard AI Evaluation\n")
    print(f"Passed: {passed}/{total}")
    print(f"Score: {passed / total * 100:.1f}%\n")
    if failures:
        print("Failed:")
        for case_id, expected, received in failures:
            print(f"{case_id}\nExpected: {expected}\nReceived: {received}\n")
    if notes:
        print("Notes (informational, did not affect score):")
        for note in notes:
            print(note)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    run(parser.parse_args().base_url)
