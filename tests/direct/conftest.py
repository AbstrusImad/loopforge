"""Actual LoopForge class, independent validator callbacks, and conservation checks."""
import copy
import hashlib
import json
import re

import pytest

PREFIX = "https://raw.githubusercontent.com/loopforge-test/passports/"
COMMIT = "a" * 40
SUPPLY = "Washed single-polymer granules have no documented incompatible additives."
NEED = "Processing accepts washed single-polymer granules with no incompatible additives."
DELIVERY = "The receiver confirms the agreed material and full requested quantity were received."
BASE = "2026-10-03T00:00:00Z"
BOND = 17


def digest(body):
    return hashlib.sha256(body.encode()).hexdigest()


class World:
    def __init__(self, vm, deploy, actors):
        self.vm = vm
        vm.warp(BASE)
        vm.sender = actors[0]
        self.events, self.transfers, self.docs = [], [], {}
        def hook(_vm, request):
            if "EmitEvent" in request:
                self.events.append(request["EmitEvent"])
                return {"ok": None}
            if "EthSend" in request:
                self.transfers.append(request["EthSend"])
                return {"ok": None}
            return None
        vm._gl_call_hook = hook
        self.contract = deploy("contracts/loopforge.py", "LoopForge test clearing")
        from genlayer import Address
        self.actors = [a if isinstance(a, Address) else Address(bytes(a)) for a in actors]
        self.call("set_source", PREFIX, True)
        self.lots, self.needs = [], []
        for i, actor in enumerate(self.actors[:3]):
            name, need_name = "LOT-" + str(i), "NEED-" + str(i)
            url, body = self.document("lot" + str(i), name + ". " + SUPPLY)
            self.lots.append(self.call("create_lot", name, "polymer", 1000, SUPPLY, url, digest(body), actor=actor))
            url, body = self.document("need" + str(i), need_name + ". " + NEED)
            self.needs.append(self.call("create_need", need_name, "polymer", 1000, 1, NEED, url, digest(body), actor=actor))

    def document(self, name, body):
        url = PREFIX + COMMIT + "/" + name + ".md"
        self.docs[url] = body
        return url, body

    def call(self, method, *args, actor=None, value=0):
        self.vm.sender = actor if actor is not None else self.actors[0]
        self.vm.value = value
        try:
            return getattr(self.contract, method)(*args)
        finally:
            self.invariants()

    def invariants(self):
        p = self.contract.get_protocol()
        assert int(p["introduced_grams"]) == sum(int(p[k]) for k in
            ("available_grams", "reserved_grams", "receipt_grams", "unreconciled_grams", "retired_grams"))
        assert int(p["paid_in_atto"]) == sum(int(p[k]) for k in
            ("bond_escrow_atto", "claimable_atto", "withdrawn_atto"))
        lots = [self.contract.get_lot(i) for i in range(1, p["lots"] + 1)]
        assert sum(r["available_grams"] for r in lots) == int(p["available_grams"])
        assert sum(r["reserved_grams"] for r in lots) == int(p["reserved_grams"])
        needs = [self.contract.get_need(i) for i in range(1, p["needs"] + 1)]
        assert sum(r["reserved_grams"] for r in needs) == int(p["reserved_grams"])
        receipts = [self.contract.get_receipt(i) for i in range(1, p["receipts"] + 1)]
        assert sum(r["unissued_grams"] for r in receipts) == int(p["receipt_grams"])

    def plan(self, grams=400, nonce="cycle-1", size=3):
        return self.call("propose_cycle", self.lots[:size],
            self.needs[1:size] + self.needs[:1], [grams] * size, BOND, 60, 60, 60, nonce)

    def mock(self, verdict="fit", kind="fit", answer=None, changed=None):
        self.vm.clear_mocks()
        for url, body in self.docs.items():
            self.vm.mock_web(re.escape(url), {"status": 200, "body": body + "CHANGED" if url == changed else body})
        quotes = {"supply": SUPPLY, "need": NEED}
        if kind == "delivery":
            quotes["delivery"] = DELIVERY
        if verdict == "uncertain":
            quotes = {}
        response = answer if answer is not None else {
            "verdict": verdict, "explanation": "Independent documents establish this bounded decision.", "quotes": quotes}
        self.vm.mock_llm("LoopForge " + kind + " review", json.dumps(response))

    def fitted(self, cycle=None):
        cycle = cycle or self.plan()
        self.mock()
        for i in range(len(self.contract.get_cycle(cycle)["owners"])):
            self.call("review_fit", cycle, i)
        return cycle

    def approved(self, cycle=None):
        cycle = self.fitted(cycle)
        row = self.contract.get_cycle(cycle)
        for address in row["owners"]:
            actor = next(a for a in self.actors if a.as_hex == address)
            self.call("approve_cycle", cycle, actor=actor, value=BOND)
        return cycle

    def locked(self, cycle=None):
        cycle = self.approved(cycle)
        self.call("lock_cycle", cycle)
        return cycle

    def delivered(self, cycle=None, verdicts=None):
        cycle = cycle or self.locked()
        row = self.contract.get_cycle(cycle)
        for i, owner in enumerate(row["owners"]):
            actor = next(a for a in self.actors if a.as_hex == owner)
            self.call("report_dispatch", cycle, i, actor=actor)
            url, body = self.document("delivery-" + str(cycle) + "-" + str(i), DELIVERY)
            self.call("submit_delivery", cycle, i, url, digest(body), actor=actor)
            self.mock((verdicts or ["conformant"] * len(row["owners"]))[i], "delivery")
            self.call("review_delivery", cycle, i)
        return cycle

    def early_settled(self):
        cycle = self.delivered()
        for actor in self.actors[:3]:
            self.call("consent_settlement", cycle, actor=actor)
        self.call("settle_cycle", cycle)
        return cycle

    def validator(self, leader, error=False):
        from genlayer import gl
        self.vm._in_nondet = True
        try:
            result = leader if error else gl.vm.Return(copy.deepcopy(leader))
            return self.vm._captured_validators[-1][2](result)
        finally:
            self.vm._in_nondet = False


@pytest.fixture
def world(direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob, direct_charlie):
    return World(direct_vm, direct_deploy, [direct_owner, direct_alice, direct_bob, direct_charlie])
