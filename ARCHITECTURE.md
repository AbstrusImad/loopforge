# The clearing boundary

LoopForge keeps a single atomic contract because a closed physical-material
exchange needs one reservation boundary. Stock, receiving capacity, wallet
consent, performance bonds, and receipt issuance share the same transaction
state. Asynchronous writes across several contracts would create intermediate
states in which only part of a circular exchange was committed.

## What is authoritative

The contract owns exact identity and quantity records, permission checks,
deadlines, consensus-result history, consent, reservations, and GEN settlement.
Document publishers own their claims about material and delivery. Validators
own independent evidence interpretation. An operator script handles credential
loading, submission, receipt polling, and non-authoritative display.

There is no frontend, centralized adjudication service, or external chain RPC.
The source curator cannot assign a verdict, settle early without participants,
redirect compensation, remove material reservations, or drain bonds.

## Two consensus-critical questions

**Fit:** does the supplied material, at the proposed quantity, satisfy the
recipient's documented processing conditions?

**Receipt:** does independently fetched evidence substantiate actual receipt
of the agreed material and quantity, meeting those conditions?

Each question captures plain records before entering a nondeterministic block.
Validators independently fetch complete source bodies and rerun the same model
task. Verdict, reason, and evidence hashes must match exactly; explanations are
bounded and citations must occur in independently fetched source text. The model
selects integer identifiers from deterministic overlapping source fragments;
the contract maps those identifiers to exact source bytes. Negative, out-of-range,
boolean, string, or unknown-label selectors are refused. Returned
model or leader extras are stripped before storage. Malformed model output
forces disagreement rather than generating a convenient uncertain agreement.

Family mismatches, minimum batch limits, available stock, and receiving capacity
are deterministic constraints. Models do not allocate quantities or calculate
GEN. Fit caches include quantity, avoiding a fit for one batch being applied to
another. Capacity and reservations are excluded from the semantic prompt because
they change with transactions; the lock operation checks them freshly.

## Commit-time versus admission-time authority

Source admission affects record creation and new cycle proposals. A proposal
copies the enabled repository prefixes into its immutable terms. Evidence
submitted for its deliveries uses that copy, so a source administrator cannot
alter evidence admissibility after a participant has bonded an exchange.
Every evidence URL still identifies a full commit and a pinned raw response hash.

## Atomic reservation and settlement

Proposal and review create no inventory reservation. Bonded signatures do not
reserve stock either. Lock first validates every leg against fresh current
stock, receiving capacity, and retirement, then performs all debits. Distinct
suppliers and unique lot/need IDs prevent repeated debits within one cycle.

Once locked, participants cannot withdraw consent or cancel. Delivery reviews
are optional inputs to deterministic deadline settlement: unresolved or failed
outgoing performance compensates that leg's receiver. Unanimous early settlement
is possible only for conformant deliveries; any new review/challenge clears all
early-settlement signatures.

Settlement reduces every lot and need reservation exactly once. Undispatched
stock is returned, conclusive receipts create bounded receiver reuse credits,
and dispatched unresolved stock is retired into the unreconciled category rather
than reminted. Each bond is converted to one claimable credit. Withdrawal is a
pull operation with state zeroed before native transfer emission.

## Accounting proof obligations

For material, original lot creation increases both introduced and available
grams. Lock moves available to reserved. Confirmed settlement moves reserved to
receipt credits, failed dispatch moves reserved to unreconciled, and unshipped
settlement moves reserved back to available. Reissue moves receipt credits to
available. Lot retirement moves available to retired. Every transition preserves
the declared-material identity.

For GEN, approval adds equal paid-in and escrow quantities. Revoke/cancel/settle
move escrow into claimable balances. Withdrawal moves claimable to withdrawn.
There are no fees, discretionary rewards, percentage splits, or rounding.

The tests assert both conservation identities after exercised writes, including
reverts, and reconcile the material totals against individual lot, need, and
receipt records. This checks implementation behavior, not physical existence or
the chain's native-transfer transport.

## Irreversible boundaries

Retired records do not reopen. Settled cycles cannot be challenged or resettled.
A reused receipt cannot issue more than its remaining grams. A failed dispatch
cannot become free inventory merely because no conclusive receipt was recorded.
An exhausted capacity or hard record bound requires a new operating deployment,
not a hidden administrator overwrite.
