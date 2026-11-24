# Golden question review

The JSONL files label generated questions as synthetic and pending human review. Use the pinned corpus or the authored policy fixtures to inspect each label.

1. Check the expected document and one-based physical page. For Markdown or HTML, use page 1.
2. Verify the answer hint directly against the source. For an abstention, search both batches for applicable evidence.
3. Verify the split. Questions about new Batch B content stay out of the Batch A run. The recorder loan duration uses its version-specific hint.
4. For at least eight synthetic rows, mark `reviewed: true`, set `review_status: human_reviewed` and record who reviewed the label in `notes`.

## Human-written questions

Rows `human-01` through `human-08` preserve the project owner's question wording. Codex checked the source labels. The credit-limit and total-degree-fee questions are abstention cases because the request lacks necessary program details. The accessibility question uses the exam-seating fixture in the Batch B split. Team review of the synthetic rows remains open.

Codex checked the answer hints for `rgo-01` through `rgo-08` against the specified handbook pages. These rows use `source_checked_by_codex` in `review_status`. The [source check record](source_checks.json) lists the results.

Faithfulness uses a cited-excerpt overlap proxy, so LLM judge agreement is outside this evaluator.
