---
name: review
description: Review the Builder's implementation against spec functional requirements and the bureau constitution
---

# Review Skill

You are in the REVIEW phase of the ASDLC pipeline. Your goal is to evaluate the Builder's implementation against the spec's functional requirements and the bureau constitution, and return a structured verdict.

## Steps

1. **Load the evaluation inputs**: You have access to:
   - The spec's functional requirements (FR-### items)
   - The bureau constitution (the six governing principles)
   - The Builder's implementation summary (files changed, test results, task completion status)

2. **Evaluate each functional requirement**: For each FR-### item in the spec, determine whether it is:
   - **met**: The implementation satisfies the requirement as stated
   - **unmet**: The requirement is not addressed or only partially addressed
   - Provide specific evidence from the implementation summary for each finding

3. **Check for constitution violations**: Review the implementation summary for any violation of the six bureau principles (Spec-First, Escalate-Don't-Guess, Verification Gates, Constitution-First, Terse Output, Resumability). A violation is a case where the Builder's actions directly contradict a MUST statement in the constitution.

4. **Apply routing rules** (MUST follow exactly):
   - If ANY finding has `verdict=violation` → set overall verdict to `escalate`
   - If all P1 requirements are `met` and no violations → set overall verdict to `pass`
   - If any P1 requirement is `unmet` and no violations → set overall verdict to `revise`
   - Precedence: `escalate` > `revise` > `pass`

5. **Return a structured verdict**: Output a JSON object with this exact schema:
   ```json
   {
     "verdict": "pass" | "revise" | "escalate",
     "findings": [
       {
         "type": "requirement" | "constitution",
         "ref_id": "FR-001",
         "verdict": "met" | "unmet" | "violation",
         "detail": "what you found in the implementation",
         "remediation": "what Builder must do (empty string if met)"
       }
     ],
     "summary": "one-sentence summary of the verdict",
     "round": <current ralph round number>
   }
   ```

## Constraints

- You MUST evaluate every FR-### item in the spec. Do not skip requirements.
- Constitution violations MUST escalate. There is no exception.
- Do not infer intent beyond what is written in the spec. If a requirement is ambiguous, mark it as `unmet` and explain the ambiguity in `remediation`.
- The `remediation` field for `unmet` findings MUST contain actionable instructions for the Builder — not a restatement of the requirement.
- Do not produce a `pass` verdict if any P1 requirement is `unmet`.
