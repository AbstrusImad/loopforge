# LoopForge

## Three factories, one simultaneous commitment

A processor has a usable polymer remainder. Its neighbour needs that material,
but offers a different remainder that a third factory can use. The third factory
can supply the first. Bilateral promises leave each factory exposed to the other
two deliveries, inventory reservations, receiving limits, and conflicting reports.

LoopForge coordinates that closed exchange as one on-chain clearing cycle.
Two to six distinct suppliers agree on exact material legs and equal performance
bonds. GenLayer independently reviews material suitability and receipt evidence.
Inventory and processing capacity reserve together; final settlement issues
material-reuse receipts and allocates each supplier's bond according to its own
outgoing delivery.

**The shipped scope is contracts, tests, operator scripts, and documentation.
StudioNet is the only configured network. There is no browser application.**

The contract is deployed on **StudioNet** at
[`0xDcD680bedDE891E51114ACF8CB400235a4c72398`](https://explorer-studio.genlayer.com/address/0xDcD680bedDE891E51114ACF8CB400235a4c72398)
using the selected main-account wallet. Its deployed source matches the local
contract byte for byte. It has **26 public methods**, **86 passing direct tests**,
and clean lint, SDK validation, and Pyright results. The corrected version passed
the full GenVM cycle, actual native-balance audit, and real default-model public
evidence test: **62 contract writes finalized**, with 55 successes and 7 expected
refusals. See [the verification record](VERIFICATION.md) and
[the public proof bundle](evidence/verification.json).

## The books must balance before the story matters

The protocol maintains two separate conserved ledgers:

```text
introduced material grams
    = available stock
    + reserved stock
    + received material awaiting reissue
    + dispatched but unreconciled material
    + retired stock

GEN ever paid in
    = performance bonds still escrowed
    + participant balances claimable
    + GEN already withdrawn
```

The first ledger records declared material quantities, not tokenized ownership
or custody of physical goods. The second is native GEN contract accounting.
The tests check both identities and reconcile aggregate stock/reservation
counters against the individual records after each exercised operation.

A failed or unproven dispatched delivery moves to **unreconciled**, never back
to available stock. An undispatched leg returns its reservation to available
stock. A confirmed receipt can become a new lot only through its receiver, and
only up to the receipt's remaining unissued quantity. Reissue moves existing
grams; it never increases the introduced-material total.

## The round, from proposal to clearing

```mermaid
stateDiagram-v2
    [*] --> Draft: propose a closed material cycle
    Draft --> Draft: independent fit reviews and bonded consent
    Draft --> Cancelled: proposer cancels or consent deadline expires
    Draft --> Locked: unanimous fit and bonds; atomic reservation
    Locked --> Locked: dispatch and receipt evidence
    Locked --> Locked: independent delivery review
    Locked --> Locked: one changed-evidence challenge per leg
    Locked --> Settled: unanimous conformant early settlement
    Locked --> Settled: receipt deadline expires; per-leg default settlement
    Settled --> [*]: withdrawals and receipt-derived material reissue
    Cancelled --> [*]: approved bonds become claimable
```

### A ring is a ring

For leg `i`, `lots[i]` belongs to supplier `owners[i]` and `needs[i]` belongs to
`owners[(i + 1) % n]`. Every supplier must be distinct. Both lot IDs and need IDs
are unique inside a cycle. The last leg returns to the first participant.
The proposer must supply a leg; an unrelated coordinator cannot bind factories.

For example, three suppliers use:

```text
lot owners:       [A, B, C]
receiving needs:  [B's need, C's need, A's need]
deliveries:       A → B, B → C, C → A
```

Each leg may exchange a different number of grams and a different material
family. There is no price oracle or assumed equal monetary value: participants
explicitly approve the entire immutable exchange.

### Fit before money

Every leg must receive `fit` before anyone can approve the cycle. Each approval
posts the **exact** configured bond. Underpayment and overpayment are refused.
Draft consent can be revoked, returning the bond to a pull-claimable balance.
The proposer can cancel a draft; after the consent deadline anyone can cancel
it to recover approved bonds.

`lock_cycle` checks all lots and receiving capacities before changing any record.
It then reserves all legs atomically. A competing cycle that used the same stock
or capacity can make a previously reviewed draft un-lockable; it cannot make the
first legs of that draft reserve while a later leg fails.

### Dispatch is not receipt

Only a leg's supplier reports dispatch. Both supplier and receiver can submit
receipt evidence, and any evaluator can invoke its review. A dispatch declaration
alone must not establish that the correct material actually arrived.

The receipt decision is `conformant`, `nonconformant`, or `uncertain`. A party to
that leg can challenge a recorded decision once, with a changed evidence hash.
Rewording the same evidence is refused. A challenge makes that leg pending and
invalidates **every** early-settlement consent in the cycle.

Early settlement requires all legs conformant and a fresh signature from every
participant. Otherwise anyone can settle after the fixed closing deadline.
Late evidence cannot reopen a settled cycle or recover unreconciled quantities.

### Who receives each bond?

| Outgoing leg at settlement | Material treatment | Bond recipient |
| --- | --- | --- |
| Dispatched and `conformant` | Issue the receiver a reusable quantity receipt | Original supplier |
| Dispatched but not conformant | Remove the reservation into unreconciled stock | Intended receiver |
| Not dispatched | Restore stock; free the receiving reservation | Intended receiver |

Each bond is allocated independently. A participant may receive its own refund
and compensation from an upstream failed leg. Settlement has no LLM call, fee,
rounding, winner selection, or discretionary curator payout.

## The judgment GenLayer actually owns

Material descriptions and processing conditions include qualitative constraints:
treatment, additives, contamination, intended process, and evidence of receipt.
A deterministic classifier cannot resolve their meaning from descriptions alone.

LoopForge uses `gl.nondet.web.request` and `gl.nondet.exec_prompt` inside a custom
`gl.vm.run_nondet_unsafe` leader/validator pair. Each validator independently:

1. Retrieves the complete commit-pinned material and processing documents, plus
   the receiving report for a delivery review.
2. Checks raw response SHA256 and document identity.
3. Reviews the same structured case with its own LLM, including exact exchange
   grams and the processing requirement.
4. Compares verdict, normalized reason, and evidence hashes exactly.
5. Checks the leader's bounded explanation and verbatim citations against its
   own independently retrieved documents.

The model selects zero-based **fragment identifiers** instead of generating
quotation text. The contract deterministically creates overlapping source
fragments (at most 480 characters each), checks each selected label/index, and
stores the exact fetched text. This avoids punctuation or markup paraphrases
breaking otherwise valid reviews. Validators still independently review the
evidence and check every stored citation against their own fetched bytes.
Legacy exact-string citations remain strictly validated for compatibility.

Explanations may differ in wording. The verdict that gates reservation or
allocates a bond may not differ. A schema-only validator is not used.

The deterministic path owns sender permissions, record uniqueness, family
constraints, minimum batches, quantities, capacity, phase windows, consent,
bond arithmetic, receipt issuance, and all storage updates. No model-generated
code is executed and no storage is written during a nondeterministic call.

Compatibility is cached by **lot ID + need ID + exchange grams**. A second cycle
cannot repeatedly sample the same case for a more convenient result, and a fit
for 400 grams cannot automatically authorize a 500-gram batch. An uncertain
cached case needs new immutable records/evidence rather than repeated sampling.

This follows GenLayer's documented focus on independently verifiable judgment
with a consequential on-chain state transition, rather than a generic AI backend.
See [When to Use GenLayer](https://docs.genlayer.com/developers/intelligent-contracts/when-to-use-genlayer)
and [Non-determinism](https://docs.genlayer.com/developers/intelligent-contracts/features/non-determinism).

## Evidence admission and failure handling

Evidence is admitted from exact GitHub repository prefixes and full lowercase
40-character commit URLs. Query strings, fragments, encoded paths, traversal,
unbounded response bodies, and non-UTF-8 data are refused. Each document is at
most 16,384 bytes. The source curator admits repositories; it cannot write a
verdict or choose a bond recipient.

The repository policy is captured **when a cycle is proposed**. A curator's later
revocation restricts new cycles and new record admission, but cannot manipulate
an existing cycle's evidence options after participants have committed money.

| Failure | Behavior |
| --- | --- |
| Changed pinned bytes | Record `uncertain` with `source_changed`; no fit or receipt clearance |
| Missing registered document identity | Record `uncertain` with `identity_missing` |
| Different declared material families | Deterministic `no_fit` / `nonconformant` |
| HTTP 4xx | `[EXTERNAL]`; independent error messages must match |
| Network failure, HTTP 429, or 5xx | `[TRANSIENT]`; independent transient failures can agree |
| Malformed model JSON or invented citation | `[LLM_ERROR]`; validators disagree, rather than lock bad state |
| Violated access, timing, or quantity rule | `[EXPECTED]` deterministic refusal |

Model explanations contain 1–800 characters. Conclusive semantic reviews require
a 16–500-character verbatim citation from **each** input document. Documents and
challenge arguments are untrusted data, never executable instructions.

## Operator surface

One atomic contract implements all subsystems. Splitting inventory and escrow
into asynchronous cross-contract writes would weaken the all-legs reservation
and conservation boundary, so there is no artificial multi-contract split.

Constructor: `LoopForge(title: str)`.

### Material and processing records

| Write | Authorized sender | Purpose |
| --- | --- | --- |
| `set_source(repository_prefix, enabled)` | Curator | Admit or revoke a document repository for future admission |
| `create_lot(name, family, grams, description, url, sha256)` | Supplier | Register an immutable original material passport |
| `create_received_lot(receipt_id, name, grams, description, url, sha256)` | Receipt receiver | Reissue existing received grams as a new passport |
| `retire_lot(lot_id)` | Lot owner | Retire unreserved stock without destroying accounting history |
| `create_need(name, family, capacity_grams, minimum_batch_grams, description, url, sha256)` | Processor | Register immutable process conditions and receiving capacity |
| `retire_need(need_id)` | Need owner | Close an unreserved need |

### Forming and executing a cycle

| Write | Authorized sender | Purpose |
| --- | --- | --- |
| `propose_cycle(lot_ids, need_ids, grams, bond_atto, accept_seconds, dispatch_seconds, receipt_seconds, nonce)` | Supplying participant | Define the closed exchange and its fixed terms |
| `review_fit(cycle_id, leg)` | Any evaluator | Independently determine quantity-specific material suitability |
| `approve_cycle(cycle_id)` | Each supplier, payable | Ratify all terms with the exact bond |
| `revoke_consent(cycle_id)` | Approved supplier, draft only | Cancel its consent and credit a bond refund |
| `cancel_cycle(cycle_id)` | Proposer, or anyone after consent expiry | Cancel the draft and credit approved bonds |
| `lock_cycle(cycle_id)` | Participant | Atomically reserve all material and receiving capacity |
| `report_dispatch(cycle_id, leg)` | Leg supplier | Record departure before the dispatch deadline |
| `submit_delivery(cycle_id, leg, url, sha256)` | Leg supplier or receiver | Pin initial receiving evidence |
| `review_delivery(cycle_id, leg)` | Any evaluator | Independently classify the receiving evidence |
| `challenge_delivery(cycle_id, leg, url, sha256, argument)` | Leg supplier or receiver | Trigger one changed-evidence reassessment |
| `consent_settlement(cycle_id)` | Each participant | Sign the currently conformant cycle for early settlement |
| `settle_cycle(cycle_id)` | Anyone after eligibility | Deterministically issue receipts and allocate bonds |
| `withdraw()` | Claimant | Pull its own claimable GEN; credit is zeroed before transfer emission |

### Views

`get_lot`, `get_need`, `get_cycle`, `get_receipt`, `get_claimable`,
`list_cycles(start, limit)`, and `get_protocol` expose current records and both
conservation ledgers. `get_cycle` includes all fit decisions, delivery-review
history, signatures, deadlines, and resulting receipt IDs. `CycleChanged` events
identify the actor, cycle, and phase; events never replace current state checks.

## Bring up the local verification environment

Recorded environment: Python 3.13, with exact versions in
[`requirements.txt`](requirements.txt).

```bash
python -m venv .venv
# PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt

python -m pytest tests/direct -q --junitxml=test-results.xml
```

The checked-in direct result contains **86 tests, zero errors, zero failures**.
Tests execute the actual contract class and explicitly invoke captured validator
callbacks with forged results. Web/model responses and native-transfer transport
are controlled. Direct tests establish contract behavior under those conditions;
they do not prove live GenVM consensus or a real outgoing balance change.

The suite checks complete two-, three-, and six-party exchanges; competing stock
and input-capacity reservations; exact bonds; atomic refusal on a stale last leg;
deadline defaults; partial-delivery compensation; changed-evidence challenges;
withdrawal replay; receipt reuse; conserved grams; and independently verified
leader fields and errors.

For cached pinned-SDK validation:

```bash
genvm-lint download --version v0.3.0-rc6
python scripts/check_contracts.py
python scripts/check_contracts.py --typecheck
```

The helper selects the cached artifact to avoid an unconditional latest-tag
lookup. Lint, SDK rules, and Pyright remain enabled. The runner is pinned in the
contract header to:

```text
py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6
```

## Network runbook — StudioNet only

Populate this project's ignored `.env` using [`.env.example`](.env.example).
The deployment operator is explicitly bound to the selected main-account public
address `0x95803126315A05E642D8E46CE1d77eA2199a2A6E`. No installed wallet session,
global environment key, or neighbouring project's file is consulted implicitly.
An alternative local credential file requires an explicit `--wallet-env` argument.

```bash
python scripts/deploy_studionet.py
gltest tests/integration -v -s --network studionet --junitxml=integration-results.xml
python scripts/verify_native_settlement.py
python scripts/exercise_default_llms.py
```

The integration scenario requires three distinct signing accounts in the project
environment, each able to post the 17 attoGEN test bond. StudioNet is gasless,
but the bond is an actual native-value transfer. The two auxiliary wallets in
this run each received 1,000 attoGEN from the main account; the finalized transfer
hashes and verified balances are recorded in `test-funding.json`. It deploys a separate test stack, provides five controlled validators
per review, and exercises real GenVM storage, consent, bonds, dispatch, challenges,
settlement, receipt reuse, refusals, and withdrawal. Its evidence is explicitly
test material; it is not a claim about factories or actual physical shipments.

Submitted hashes are journaled before polling. Deployment resumes only when its
network, account, and source hash match. The integration helper verifies the
deployed source and resumes its existing journal, checking the method, signer,
value and successful consensus execution before skipping a step. Temporary RPC read failures
are retried without resending signed transactions. Archive a completed journal
only when intentionally starting a separate test deployment. Integration and
public-evidence steps advance on consensus acceptance, use accepted state for
intermediate assertions, and then explicitly verify every recorded transaction
is `FINALIZED` before reporting success. Native balance audits read finalized
state. RPC requests are paced. Lifecycle and execution `SUCCESS` are checked separately;
expected errors must contain the intended contract refusal.

For an existing real-data cycle:

```bash
python scripts/review_default_llms.py 1
```

That script uses the network's default LLMs and independently fetched public
documents, with no model or web mocks. It only evaluates still-pending fit legs
and records actual outcomes. It does not invent passports, factories, successful
deliveries, deployed addresses, or a positive fit result.

All network helpers verify **RPC `https://studio.genlayer.com/api`, chain ID
`61999`**, before signing. The contract's payable path uses native GEN within
that network; no third-party chain or external EVM RPC is configured.

## Boundaries the ledger cannot remove

Material existence, original quantity, and the truthfulness of documents remain
physical-world assumptions. A source curator's admission is an evidence-authority
decision, not proof that a factory or inspector is honest. Participants must be
comfortable with the named source authorities and the fixed deadline defaults
before posting bonds.

The protocol does not certify industrial safety, legal compliance, transport,
ownership, or commercial price. It does not automatically discover exchanges,
operate machinery, scan physical shipments, or compel a receiver to supply
evidence. There is no discretionary curator recovery path or administrative
withdrawal of participant bonds.

Evidence outages can prevent a timely conclusive receipt review. If a dispatched
leg remains unresolved at close, its quantity becomes unreconciled and its bond
compensates the intended receiver. This is an explicit contract term, not a
finding that the physical shipment did not occur.

| Resource | Enforced bound |
| --- | --- |
| Cycle legs | 2–6 distinct suppliers |
| Material and need records | 4,096 each |
| Cycles | 1,024 |
| Evidence repositories | 32 admitted prefixes |
| Document size | 16 KiB per response |
| Each quantity/capacity/minimum | Positive integer grams, at most `10^15` |
| Each bond | Positive integer atto-GEN, at most `10^24` |
| Each phase window | 60–604,800 seconds |
| Material families | metal, polymer, glass, mineral, biomass, textile |
| Delivery challenges | One per cycle leg, changed evidence required |
| Cycle pagination | At most 32 records per page |

Aggregate gram and GEN values leave the contract as decimal strings to avoid
JSON precision loss. Worst-case execution cost and real native-transfer behavior
still require StudioNet verification before production claims.

## Project records

| File | Role |
| --- | --- |
| [`contracts/loopforge.py`](contracts/loopforge.py) | Atomic clearing implementation |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Consensus boundary and invariant reasoning |
| [`NOVELTY.md`](NOVELTY.md) | Distinction from prior projects |
| [`VERIFICATION.md`](VERIFICATION.md) | Honest local and network verification status |
| [`lint-results.json`](lint-results.json) | SDK interface and safety lint result |
| [`typecheck-results.json`](typecheck-results.json) | Pyright diagnostics |
| [`test-results.xml`](test-results.xml) | Recorded direct-mode test outcomes |
| [`tests/integration/test_studionet.py`](tests/integration/test_studionet.py) | Explicit controlled GenVM scenario |

Deployment and activity records contain actual network receipts. Superseded v1
source/receipts are isolated in [`evidence/archive-v1`](evidence/archive-v1/README.md);
the main verification bundle concerns the corrected version only.
There are no placeholder addresses or fabricated transaction hashes in this
project. Local environment files, signing material, caches, and private
credentials are ignored by Git.

Released under the [MIT License](LICENSE).

## Observed StudioNet results

| Run | What was established |
| --- | --- |
| Controlled GenVM cycle | Three distinct signing owners; 38 finalized writes; atomic reservation; receipt reviews using fragment IDs; changed-evidence challenge; fresh settlement consent; receipt reuse |
| Native balance audit | All 51 attoGEN of bonds returned to their owners; actual contract balance zero; replay refused; all seven views exercised |
| Default GenLayer models | Genuine public HTTP documents; no model/web mocks; verdicts `no_fit`, `uncertain`, `uncertain`; consent and lock refused; cancelled demonstration records retired |

All 19 write entrypoints were exercised across the runs. The on-network
`revoke_consent` case verifies refusal without prior consent; successful draft
revocation/refund is covered by the direct tests. Positive physical-delivery
adjudication uses clearly marked controlled fixtures. Public educational
documents do not certify a real batch or shipment, and the real-model test
correctly does not clear that exchange.

The controlled test deployment is
[`0x4eBE7B8fdE7e5905c5Be4635A0e22A7c419994F1`](https://explorer-studio.genlayer.com/address/0x4eBE7B8fdE7e5905c5Be4635A0e22A7c419994F1).
