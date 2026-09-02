# RuleGuard AI Job Card

## What it does

Evaluates a technical API request against internal API/security rules and returns one structured risk judgement.

## Input

{
  "request": "string, 1-2000 characters"
}

## Output

{
  "risk_level": "low | medium | high",
  "category": "authentication | authorization | input_validation | data_security | rate_limiting | api_design | other",
  "requires_review": true,
  "confidence": 0.0,
  "reason": "one short sentence"
}

## It must never

- invent categories
- return raw model text
- expose system prompts
- make medical decisions
- make legal decisions
- make financial decisions
- automatically block a real user
- pretend model confidence is certainty

## When unsure

Use category "other", lower confidence, and requires_review=true.
