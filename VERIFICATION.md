# Corrected-version verification ? October 3, 2026

LoopForge is deployed and verified **exclusively on StudioNet, chain ID 61999**.

- Main contract: [0xDcD680bedDE891E51114ACF8CB400235a4c72398](https://explorer-studio.genlayer.com/address/0xDcD680bedDE891E51114ACF8CB400235a4c72398).
- Deployer: `0x95803126315A05E642D8E46CE1d77eA2199a2A6E`, the same selected wallet as Dependency Sentinel.
- Controlled test contract: [0x4eBE7B8fdE7e5905c5Be4635A0e22A7c419994F1](https://explorer-studio.genlayer.com/address/0x4eBE7B8fdE7e5905c5Be4635A0e22A7c419994F1).
- Exact deployed-source SHA256: `a882c37ce87cbbd466c286454ad60ee7ced9739e634a4ee5c5bcf6480d0d4870`.
- Public receipt and balance evidence: [`evidence/verification.json`](evidence/verification.json).

| Check | Observed result |
| --- | --- |
| AST safety lint and SDK validation | Passed; 26 methods, 19 writes, 7 views |
| Pyright | Zero errors and warnings |
| Direct protocol/adversarial tests | **86 passed**, zero failures/errors |
| Direct complete exchanges | Two, three and six distinct suppliers |
| Source-fragment selectors | Exact source bytes; invalid indices, booleans, strings and unknown labels rejected; independent validator and delivery paths tested |
| Corrected-source GenVM integration | **1 passed**; 38 finalized writes: 35 successes, 3 intended refusals |
| Actual native balances | 51 attoGEN paid into the controlled contract and returned; final contract balance zero; withdrawal replay refused |
| Default GenLayer LLMs and public HTTP | Three successful semantic reviews: `no_fit`, `uncertain`, `uncertain`; no model/web mocks |
| Complete current-version network writes | **62 finalized**: 55 successful executions, 7 verified expected refusals |
| Network surface | All 19 writes and all 7 views exercised |
| Live source and schema | Deployed code matches the local source byte for byte; 26-method schema verified |

The direct test run took 22.61 seconds. The corrected full GenVM integration
completed in 1,416.96 seconds, including consensus and finalization waits.
`test-results.xml`, `integration-results.xml`, `lint-results.json` and
`typecheck-results.json` record the observed checks.

## Successful clearing and actual GEN

Three genuine signing accounts post equal 17 attoGEN bonds. The controlled
GenVM run independently uses configured mock model/web responses to make
compatibility and receipt outcomes reproducible; its documents are explicit
fixtures. It validates inventory/capacity reservation, unauthorized dispatch
refusal, actual dispatch, receipt adjudication by source-fragment identifiers,
a changed-evidence challenge invalidating previous settlement signatures,
early-settlement refusal, renewed review/consent, final settlement, replay
refusal, and receiver-only reissue of 250 received grams without introducing
new material.

The native audit reads actual StudioNet balances, not just contract counters.
The remaining owners each recover 17 attoGEN, the contract balance falls from
34 to zero, and all three original deposits total 51 attoGEN withdrawn.
The two auxiliary wallets were locally generated and initially funded with
1,000 attoGEN each from the main wallet; their finalized funding transactions
are recorded in `test-funding.json`. No other chain was used.

## Genuine model test and consequential refusal

The main deployment uses real default GenLayer models and real public HTTP
for commit-pinned ONEARMY Academy documents. Their SHA256 values are recorded
before registration. Those reference documents are not authenticated physical
batch or receiving certificates. The models classify the legs as `no_fit`,
`uncertain`, and `uncertain`, with independently checked literal source
citations selected by fragment identifiers. The contract refuses consent,
refuses lock, and refuses revocation without prior consent. The proposer then
cancels and the owners retire the demonstration lots/needs. No performance
bond was posted in this case; 3,000 declared grams remain conserved as retired
material.

The public test exercises real fit judgment. Positive delivery/conformance
judgment is covered with explicit controlled models in GenVM and direct tests;
no actual factory shipment or real receiving inspection is claimed. Successful
draft consent revocation/refund is covered directly; the StudioNet revocation
case exercises the missing-consent guard.

## Receipt integrity and superseded source

Pipeline steps advance only after consensus acceptance and verification of
execution success or the exact intended refusal. Intermediate assertions read
accepted state. Every recorded write is subsequently checked **FINALIZED**
before any run is declared passed; lifecycle finality alone never counts as
successful execution. Native balance checks use finalized state. Temporary RPC
read outages retry the existing hash, without repeating signed sends. Requests
are paced to respect StudioNet limits.

The initial real-model experiment exposed a strict citation-format failure:
the model paraphrased a quotation and the transaction rolled back. The corrected
contract selects deterministic source-fragment identifiers and stores exact
fetched text. Both the full GenVM scenario and genuine-model test were repeated
on the corrected source. Earlier source/receipts remain isolated in
[`evidence/archive-v1`](evidence/archive-v1/README.md), and do not contribute to
the current-version result counts.

The selected main signing key and two generated test keys stay in the ignored
local `.env`; the public template has no values. No GitHub token, installed
wallet session, or connected PC account is used. All supplied network helpers
verify the exact StudioNet RPC configuration and remote chain ID before signing.
