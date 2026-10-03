import copy
import json

import pytest

from conftest import BOND, COMMIT, DELIVERY, NEED, PREFIX, SUPPLY, digest


def test_complete_three_party_exchange_and_material_reuse(world):
    cycle = world.early_settled()
    p = world.contract.get_protocol()
    assert (p["receipts"], p["receipt_grams"], p["reserved_grams"]) == (3, "1200", "0")
    row = world.contract.get_cycle(cycle)
    assert row["phase"] == "settled" and row["accepted_legs"] == 3
    receipt = world.contract.get_receipt(row["receipt_ids"][0])
    receiver = world.actors[1]
    url, body = world.document("new-passport", "REUSED. " + SUPPLY)
    lot = world.call("create_received_lot", receipt["id"], "REUSED", 250, SUPPLY, url, digest(body), actor=receiver)
    assert world.contract.get_lot(lot)["parent_receipt"] == receipt["id"]
    assert world.contract.get_receipt(receipt["id"])["unissued_grams"] == 150
    assert world.contract.get_protocol()["introduced_grams"] == "3000"


@pytest.mark.parametrize("grams", [0, -1, 10**15 + 1, True])
def test_quantities_are_bounded_positive_integer_grams(world, grams):
    url, body = world.document("bad-quantity", "INVALID. " + SUPPLY)
    with pytest.raises(Exception, match="positive grams"):
        world.call("create_lot", "INVALID", "polymer", grams, SUPPLY, url, digest(body))


@pytest.mark.parametrize("url", ["http://localhost/x", PREFIX + "main/a.md", PREFIX + COMMIT + "/../x", PREFIX + COMMIT + "/x?q=1", PREFIX + COMMIT + "/%2e%2e/x"])
def test_evidence_urls_cannot_escape_pinned_public_documents(world, url):
    with pytest.raises(Exception, match="commit|canonical"):
        world.call("create_lot", "INVALID", "polymer", 1, SUPPLY, url, "f" * 64)


def test_passport_cannot_mint_stock_twice(world):
    lot = world.contract.get_lot(1)
    with pytest.raises(Exception, match="already issued"):
        world.call("create_lot", "OTHER", "polymer", 1000, SUPPLY, lot["url"], lot["sha256"])


def test_huge_whitespace_does_not_bypass_text_bounds(world):
    url, body = world.document("oversize", "OTHER. " + SUPPLY)
    with pytest.raises(Exception, match="material description"):
        world.call("create_lot", "OTHER", "polymer", 1, SUPPLY + " " * 3000, url, digest(body))


def test_curator_cannot_change_existing_cycle_evidence_policy(world):
    cycle = world.locked()
    world.call("set_source", PREFIX, False)
    world.call("report_dispatch", cycle, 0)
    url, body = world.document("grandfathered", DELIVERY)
    world.call("submit_delivery", cycle, 0, url, digest(body))
    with pytest.raises(Exception, match="repository no longer"):
        world.plan(nonce="new-cycle")


def test_only_curator_admits_sources(world):
    with pytest.raises(Exception, match="curator only"):
        world.call("set_source", PREFIX, False, actor=world.actors[1])


def test_one_supplier_cannot_pose_as_every_cycle_participant(world):
    url, body = world.document("second-owned-lot", "SECOND. " + SUPPLY)
    second = world.call("create_lot", "SECOND", "polymer", 1, SUPPLY, url, digest(body))
    with pytest.raises(Exception, match="distinct"):
        world.call("propose_cycle", [1, second], [1, 2], [1, 1], BOND, 60, 60, 60, "repeated")


def test_duplicate_lot_ids_are_rejected_separately(world):
    with pytest.raises(Exception, match="unique"):
        world.call("propose_cycle", [1, 1], [1, 2], [1, 1], BOND, 60, 60, 60, "duplicate")


def test_cycle_must_close_at_the_next_participant(world):
    with pytest.raises(Exception, match="next participant"):
        world.call("propose_cycle", world.lots, world.needs, [100] * 3, BOND, 60, 60, 60, "not-closed")


def test_outsider_cannot_propose_or_ratify_a_cycle(world):
    with pytest.raises(Exception, match="proposer must"):
        world.call("propose_cycle", world.lots, [2, 3, 1], [100] * 3, BOND, 60, 60, 60, "outsider", actor=world.actors[3])
    cycle = world.fitted()
    with pytest.raises(Exception, match="participant only"):
        world.call("approve_cycle", cycle, actor=world.actors[3], value=BOND)


def test_nonce_is_bound_to_the_proposer(world):
    world.plan()
    with pytest.raises(Exception, match="nonce already"):
        world.plan()


@pytest.mark.parametrize("bad", [0, 59, 604801, True])
def test_phase_windows_have_hard_bounds(world, bad):
    with pytest.raises(Exception, match="phase windows"):
        world.call("propose_cycle", world.lots, [2, 3, 1], [100] * 3, BOND, bad, 60, 60, "bad-window")


def test_consent_requires_every_leg_to_fit(world):
    cycle = world.plan()
    world.mock("no_fit")
    world.call("review_fit", cycle, 0)
    with pytest.raises(Exception, match="every material"):
        world.call("approve_cycle", cycle, value=BOND)


@pytest.mark.parametrize("value", [0, BOND - 1, BOND + 1])
def test_bond_is_exact_not_at_least(world, value):
    cycle = world.fitted()
    with pytest.raises(Exception, match="exact performance"):
        world.call("approve_cycle", cycle, value=value)
    assert world.contract.get_protocol()["paid_in_atto"] == "0"


def test_double_approval_and_incomplete_consent_are_rejected(world):
    cycle = world.fitted()
    world.call("approve_cycle", cycle, value=BOND)
    with pytest.raises(Exception, match="already approved"):
        world.call("approve_cycle", cycle, value=BOND)
    with pytest.raises(Exception, match="unanimous"):
        world.call("lock_cycle", cycle)


def test_revoke_returns_bond_and_cancels_lock_eligibility(world):
    cycle = world.approved()
    world.call("revoke_consent", cycle, actor=world.actors[1])
    assert world.contract.get_claimable(world.actors[1].as_hex) == str(BOND)
    with pytest.raises(Exception, match="unanimous"):
        world.call("lock_cycle", cycle)
    world.call("cancel_cycle", cycle)
    assert world.contract.get_protocol()["bond_escrow_atto"] == "0"


def test_cancellation_is_proposer_only_until_deadline(world):
    cycle = world.approved()
    with pytest.raises(Exception, match="proposer only"):
        world.call("cancel_cycle", cycle, actor=world.actors[1])
    world.vm.warp("2026-10-03T00:01:01Z")
    world.call("cancel_cycle", cycle, actor=world.actors[3])
    assert world.contract.get_cycle(cycle)["phase"] == "cancelled"


def test_competing_cycles_cannot_double_reserve_stock(world):
    one = world.plan(grams=700)
    two = world.plan(grams=700, nonce="competing")
    world.locked(one)
    world.approved(two)
    before = world.contract.get_protocol()
    with pytest.raises(Exception, match="stock or capacity changed"):
        world.call("lock_cycle", two)
    assert world.contract.get_protocol() == before
    assert world.contract.get_cycle(two)["phase"] == "draft"


def test_stale_last_leg_causes_no_partial_reservation(world):
    cycle = world.approved()
    world.call("retire_lot", 3, actor=world.actors[2])
    before = world.contract.get_protocol()
    with pytest.raises(Exception, match="retired"):
        world.call("lock_cycle", cycle)
    assert world.contract.get_protocol() == before
    assert world.contract.get_lot(1)["reserved_grams"] == 0


def test_reserved_lots_and_needs_cannot_be_retired(world):
    world.locked()
    with pytest.raises(Exception, match="reserved"):
        world.call("retire_lot", 1)
    with pytest.raises(Exception, match="reserved"):
        world.call("retire_need", 2, actor=world.actors[1])


def test_passport_retirement_conserves_quantity(world):
    world.call("retire_lot", 1)
    assert world.contract.get_protocol()["retired_grams"] == "1000"


def test_only_each_leg_supplier_can_dispatch(world):
    cycle = world.locked()
    with pytest.raises(Exception, match="supplier only"):
        world.call("report_dispatch", cycle, 0, actor=world.actors[1])
    world.call("report_dispatch", cycle, 0)
    with pytest.raises(Exception, match="already dispatched"):
        world.call("report_dispatch", cycle, 0)


def test_dispatch_deadline_and_locked_cancellation_are_enforced(world):
    cycle = world.locked()
    with pytest.raises(Exception, match="draft cycle"):
        world.call("cancel_cycle", cycle)
    world.vm.warp("2026-10-03T00:02:01Z")
    with pytest.raises(Exception, match="dispatch window"):
        world.call("report_dispatch", cycle, 0)


def test_delivery_requires_dispatch_and_bilateral_authority(world):
    cycle = world.locked()
    url, body = world.document("delivery", DELIVERY)
    with pytest.raises(Exception, match="dispatch required"):
        world.call("submit_delivery", cycle, 0, url, digest(body))
    world.call("report_dispatch", cycle, 0)
    with pytest.raises(Exception, match="supplier or receiver"):
        world.call("submit_delivery", cycle, 0, url, digest(body), actor=world.actors[2])
    world.call("submit_delivery", cycle, 0, url, digest(body), actor=world.actors[1])


def test_early_settlement_needs_unanimous_receipt_specific_consent(world):
    cycle = world.delivered()
    world.call("consent_settlement", cycle)
    with pytest.raises(Exception, match="window or unanimous"):
        world.call("settle_cycle", cycle)
    for actor in world.actors[1:3]:
        world.call("consent_settlement", cycle, actor=actor)
    assert world.call("settle_cycle", cycle)["accepted_legs"] == 3


def test_undispatched_default_restores_stock_and_compensates_receivers(world):
    cycle = world.locked()
    world.vm.warp("2026-10-03T00:03:01Z")
    world.call("settle_cycle", cycle, actor=world.actors[3])
    p = world.contract.get_protocol()
    assert (p["available_grams"], p["reserved_grams"], p["receipt_grams"]) == ("3000", "0", "0")
    assert all(world.contract.get_claimable(a.as_hex) == str(BOND) for a in world.actors[:3])


def test_dispatched_but_unproven_material_is_never_reminted(world):
    cycle = world.locked()
    world.call("report_dispatch", cycle, 0)
    world.vm.warp("2026-10-03T00:03:01Z")
    world.call("settle_cycle", cycle)
    p = world.contract.get_protocol()
    assert (p["available_grams"], p["unreconciled_grams"], p["receipt_grams"]) == ("2600", "400", "0")
    assert world.contract.get_lot(1)["available_grams"] == 600


def test_partial_failure_compensation_is_per_outgoing_leg(world):
    cycle = world.delivered(verdicts=["nonconformant", "conformant", "conformant"])
    world.vm.warp("2026-10-03T00:03:01Z")
    result = world.call("settle_cycle", cycle)
    assert result["accepted_legs"] == 2
    assert world.contract.get_claimable(world.actors[0].as_hex) == "0"
    assert world.contract.get_claimable(world.actors[1].as_hex) == str(BOND * 2)
    assert world.contract.get_claimable(world.actors[2].as_hex) == str(BOND)
    assert world.contract.get_protocol()["unreconciled_grams"] == "400"


def test_challenge_invalidates_every_early_settlement_signature(world):
    cycle = world.delivered()
    for actor in world.actors[:3]:
        world.call("consent_settlement", cycle, actor=actor)
    url, body = world.document("new-delivery", DELIVERY + " Revised receiving inspection.")
    world.call("challenge_delivery", cycle, 0, url, digest(body), "A new receiving inspection documents a material discrepancy.", actor=world.actors[1])
    row = world.contract.get_cycle(cycle)
    assert not any(row["settlement_consents"]) and row["deliveries"][0]["verdict"] == "pending"
    with pytest.raises(Exception, match="all receipts"):
        world.call("consent_settlement", cycle)
    world.mock("nonconformant", "delivery")
    world.call("review_delivery", cycle, 0)
    assert len(world.contract.get_cycle(cycle)["deliveries"][0]["reviews"]) == 2
    url, body = world.document("third-delivery", DELIVERY + " Third report.")
    with pytest.raises(Exception, match="one challenge"):
        world.call("challenge_delivery", cycle, 0, url, digest(body), "Attempt another review of the same delivery.")


def test_challenge_requires_new_evidence_not_rewording(world):
    cycle = world.delivered()
    delivery = world.contract.get_cycle(cycle)["deliveries"][0]
    with pytest.raises(Exception, match="changed evidence"):
        world.call("challenge_delivery", cycle, 0, delivery["url"], delivery["sha256"], "Please reconsider exactly the same evidence.")


def test_receipt_credits_are_not_transferable_or_reusable_twice(world):
    world.early_settled()
    url, body = world.document("reuse", "REUSED. " + SUPPLY)
    with pytest.raises(Exception, match="receipt owner"):
        world.call("create_received_lot", 1, "REUSED", 400, SUPPLY, url, digest(body))
    with pytest.raises(Exception, match="quantity exhausted"):
        world.call("create_received_lot", 1, "REUSED", 401, SUPPLY, url, digest(body), actor=world.actors[1])
    world.call("create_received_lot", 1, "REUSED", 400, SUPPLY, url, digest(body), actor=world.actors[1])
    url, body = world.document("reuse2", "REUSED2. " + SUPPLY)
    with pytest.raises(Exception, match="quantity exhausted"):
        world.call("create_received_lot", 1, "REUSED2", 1, SUPPLY, url, digest(body), actor=world.actors[1])


def test_settlement_and_withdrawal_cannot_be_replayed(world):
    cycle = world.early_settled()
    with pytest.raises(Exception, match="awaiting settlement"):
        world.call("settle_cycle", cycle)
    world.call("withdraw")
    assert len(world.transfers) == 1
    assert world.contract.get_claimable(world.actors[0].as_hex) == "0"
    assert world.contract.get_protocol()["withdrawn_atto"] == str(BOND)
    with pytest.raises(Exception, match="nothing claimable"):
        world.call("withdraw")


def test_fit_cache_prevents_repeated_sampling_of_one_passport_pair(world):
    first = world.fitted()
    second = world.plan(nonce="second")
    world.mock("no_fit")
    assert world.call("review_fit", second, 0)["verdict"] == "fit"
    assert world.contract.get_cycle(first)["fits"][0]["verdict"] == "fit"


def test_changed_document_records_uncertain_without_clearance(world):
    cycle = world.plan()
    world.mock(changed=world.contract.get_lot(1)["url"])
    result = world.call("review_fit", cycle, 0)
    assert result["verdict"] == "uncertain" and result["reason"] == "source_changed"


@pytest.mark.parametrize("answer", [None, [], {"verdict": "fit"}, {"verdict": "magic", "explanation": "x", "quotes": {}},
    {"verdict": "fit", "explanation": "x", "quotes": {"supply": "a fake supporting quotation", "need": NEED}},
    {"verdict": "fit", "explanation": "x", "quotes": {"supply": SUPPLY}},
    {"verdict": "uncertain", "explanation": "x", "quotes": {"invented": SUPPLY}}])
def test_malformed_or_ungrounded_models_do_not_change_state(world, answer):
    cycle = world.plan()
    world.vm.clear_mocks()
    for url, body in world.docs.items():
        import re
        world.vm.mock_web(re.escape(url), {"status": 200, "body": body})
    world.vm.mock_llm("LoopForge fit review", json.dumps(answer))
    with pytest.raises(Exception, match="LLM_ERROR"):
        world.call("review_fit", cycle, 0)
    assert world.contract.get_cycle(cycle)["fits"][0]["verdict"] == "pending"


@pytest.mark.parametrize("field,value", [("verdict", "no_fit"), ("reason", "invented"),
    ("evidence_hashes", ["f" * 64]), ("explanation", ""),
    ("quotes", {"supply": "This quotation is fabricated.", "need": NEED}),
    ("quotes", {"supply": SUPPLY})])
def test_independent_validator_refuses_forged_leader_fields(world, field, value):
    cycle = world.plan()
    world.mock()
    result = world.call("review_fit", cycle, 0)
    forged = copy.deepcopy(result)
    forged[field] = value
    assert world.validator(forged) is False


def test_validators_accept_different_grounded_explanation_wording(world):
    cycle = world.plan()
    world.mock()
    result = world.call("review_fit", cycle, 0)
    result["explanation"] = "The pinned supply and processing documents substantiate this same decision."
    assert world.validator(result) is True


@pytest.mark.parametrize("status,prefix", [(403, "EXTERNAL"), (404, "EXTERNAL"), (429, "TRANSIENT"), (503, "TRANSIENT")])
def test_external_failures_never_unlock_a_cycle(world, status, prefix):
    cycle = world.plan()
    world.vm.clear_mocks()
    world.vm.mock_web("raw.githubusercontent.com", {"status": status, "body": "unavailable"})
    with pytest.raises(Exception, match=prefix):
        world.call("review_fit", cycle, 0)
    assert world.contract.get_cycle(cycle)["fits"][0]["verdict"] == "pending"


def test_pages_and_unknown_records_fail_readably(world):
    world.plan()
    assert len(world.contract.list_cycles(1, 32)) == 1
    with pytest.raises(Exception, match="invalid page"):
        world.contract.list_cycles(0, 33)
    for method in ("get_lot", "get_need", "get_cycle", "get_receipt"):
        with pytest.raises(Exception, match="unknown"):
            world.call(method, 999)


def test_family_mismatch_cannot_be_overridden_by_model_fit(world):
    url, body = world.document("metal-need", "METAL-NEED. " + NEED)
    need = world.call("create_need", "METAL-NEED", "metal", 1000, 1, NEED, url, digest(body), actor=world.actors[1])
    cycle = world.call("propose_cycle", world.lots, [need, 3, 1], [100] * 3, BOND, 60, 60, 60, "mismatch")
    world.mock("fit")
    result = world.call("review_fit", cycle, 0)
    assert result["verdict"] == "no_fit" and result["reason"] == "family_mismatch"


def test_validator_really_reruns_model_instead_of_trusting_shape(world):
    cycle = world.plan()
    world.mock("fit")
    leader = world.call("review_fit", cycle, 0)
    world.mock("no_fit")
    assert world.validator(leader) is False


def test_two_party_cycle_is_also_a_closed_exchange(world):
    cycle = world.plan(size=2)
    world.locked(cycle)
    world.delivered(cycle)
    world.vm.warp("2026-10-03T00:03:01Z")
    assert world.call("settle_cycle", cycle)["accepted_legs"] == 2


def test_receipt_deadline_blocks_review_and_challenge(world):
    cycle = world.delivered()
    world.vm.warp("2026-10-03T00:03:01Z")
    with pytest.raises(Exception, match="receipt review window"):
        world.call("review_delivery", cycle, 0)
    url, body = world.document("late", DELIVERY + " Late inspection.")
    with pytest.raises(Exception, match="evidence window"):
        world.call("challenge_delivery", cycle, 0, url, digest(body), "A report supplied after the fixed closing time.")


@pytest.mark.parametrize("message,expected", [("[TRANSIENT] different network failure", True),
    ("[EXTERNAL] evidence HTTP 404", False), ("[LLM_ERROR] malformed review JSON", False)])
def test_validator_error_agreement_uses_independent_failure_class(world, message, expected):
    from types import SimpleNamespace
    cycle = world.plan()
    world.mock()
    world.call("review_fit", cycle, 0)
    world.vm.clear_mocks()
    world.vm.mock_web("raw.githubusercontent.com", {"status": 503, "body": "unavailable"})
    assert world.validator(SimpleNamespace(message=message), error=True) is expected


def test_receiving_capacity_is_reserved_even_with_independent_supply_lots(world):
    original = world.plan(grams=700)
    other_lots = []
    for i, actor in enumerate(world.actors[:3]):
        name = "SECOND-" + str(i)
        url, body = world.document("second" + str(i), name + ". " + SUPPLY)
        other_lots.append(world.call("create_lot", name, "polymer", 1000, SUPPLY, url, digest(body), actor=actor))
    other = world.call("propose_cycle", other_lots, [2, 3, 1], [400] * 3, BOND, 60, 60, 60, "capacity-race")
    world.locked(original)
    world.approved(other)
    with pytest.raises(Exception, match="stock or capacity changed"):
        world.call("lock_cycle", other)
    assert all(world.contract.get_lot(i)["available_grams"] == 1000 for i in other_lots)


def test_full_six_party_exchange_conserves_material_and_bonds(world):
    from genlayer import Address
    world.actors.extend([Address(bytes([35]) * 20), Address(bytes([36]) * 20)])
    for i in range(3, 6):
        actor, name, need_name = world.actors[i], "LOT-" + str(i), "NEED-" + str(i)
        url, body = world.document("lot" + str(i), name + ". " + SUPPLY)
        world.lots.append(world.call("create_lot", name, "polymer", 1000, SUPPLY, url, digest(body), actor=actor))
        url, body = world.document("need" + str(i), need_name + ". " + NEED)
        world.needs.append(world.call("create_need", need_name, "polymer", 1000, 1, NEED, url, digest(body), actor=actor))
    cycle = world.plan(size=6)
    world.locked(cycle)
    world.delivered(cycle)
    for actor in world.actors:
        world.call("consent_settlement", cycle, actor=actor)
    assert world.call("settle_cycle", cycle)["accepted_legs"] == 6
    assert world.contract.get_protocol()["receipt_grams"] == "2400"
    assert world.contract.get_protocol()["claimable_atto"] == str(6 * BOND)


def test_small_batches_cannot_be_approved_around_native_minimum(world):
    url, body = world.document("minimum", "MINIMUM-NEED. " + NEED)
    need = world.call("create_need", "MINIMUM-NEED", "polymer", 1000, 500, NEED, url, digest(body), actor=world.actors[1])
    with pytest.raises(Exception, match="minimum batch"):
        world.call("propose_cycle", world.lots, [need, 3, 1], [400] * 3, BOND, 60, 60, 60, "too-small")


def test_semantic_fit_cache_is_quantity_specific(world):
    first = world.fitted()
    second = world.plan(grams=500, nonce="different-quantity")
    world.mock("no_fit")
    assert world.call("review_fit", second, 0)["verdict"] == "no_fit"
    assert world.contract.get_cycle(first)["fits"][0]["verdict"] == "fit"


def test_fragment_identifiers_store_actual_source_bytes(world):
    cycle = world.plan()
    world.mock(answer={"verdict": "fit", "explanation": "Selected pinned fragments support compatibility.",
                       "quote_ids": {"supply": 0, "need": 0}})
    result = world.call("review_fit", cycle, 0)
    assert result["quotes"] == {"supply": world.docs[world.contract.get_lot(1)["url"]],
                               "need": world.docs[world.contract.get_need(2)["url"]]}
    assert "quote_ids" not in result
    assert world.validator(result)


@pytest.mark.parametrize("ids", [{"supply": -1, "need": 0}, {"supply": 10000, "need": 0},
    {"supply": True, "need": 0}, {"supply": "0", "need": 0}, {"unknown": 0}, []])
def test_forged_fragment_identifiers_are_rejected(world, ids):
    cycle = world.plan()
    world.mock(answer={"verdict": "fit", "explanation": "This invalid selector must not alter storage.", "quote_ids": ids})
    with pytest.raises(Exception, match="citation identifier"):
        world.call("review_fit", cycle, 0)
    assert world.contract.get_cycle(cycle)["fits"][0]["verdict"] == "pending"


def test_uncertain_review_can_omit_fragment_identifiers(world):
    cycle = world.plan()
    world.mock(answer={"verdict": "uncertain", "explanation": "No batch-specific evidence establishes suitability.", "quote_ids": {}})
    assert world.call("review_fit", cycle, 0)["quotes"] == {}


def test_fragment_delivery_review_preserves_exact_receiving_evidence(world):
    cycle = world.locked()
    world.call("report_dispatch", cycle, 0)
    url, body = world.document("fragment-receipt", DELIVERY)
    world.call("submit_delivery", cycle, 0, url, digest(body))
    world.mock(kind="delivery", answer={"verdict": "conformant", "explanation": "Pinned receiving evidence confirms the agreed material.",
                                       "quote_ids": {"supply": 0, "need": 0, "delivery": 0}})
    result = world.call("review_delivery", cycle, 0)
    assert result["quotes"]["delivery"] == body
    assert world.validator(result)
