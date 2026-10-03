"""Real GenVM, three real owners, controlled documents/models; StudioNet exclusively."""
import hashlib
import json
from pathlib import Path
import sys

from gltest.utils import extract_contract_address
from gltest.validators import ValidatorFactory

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from genlayer_py.types import TransactionStatus, TransactionHashVariant
from _studio import ROOT, connect, participants, read as read_state, save, wait, write, finalize_journal


def read(client, address, method, args=None):
    return read_state(client, address, method, args, variant=TransactionHashVariant.LATEST_NONFINAL)

PREFIX = "https://raw.githubusercontent.com/loopforge-integration/evidence/"
COMMIT = "b" * 40
SUPPLY = "Washed single-polymer granules have no documented incompatible additives."
NEED = "Processing accepts washed single-polymer granules with no incompatible additives."
DELIVERY = "The receiver confirms the agreed material and full requested quantity were received."


def digest(body):
    return hashlib.sha256(body.encode()).hexdigest()


def context(documents, kind, verdict):
    quotes = {"supply": SUPPLY, "need": NEED}
    if kind == "delivery":
        quotes["delivery"] = DELIVERY
    validators = ValidatorFactory().batch_create_mock_validators(count=5,
        mock_llm_response={"nondet_exec_prompt": {"LoopForge " + kind + " review": json.dumps({
            "verdict": verdict, "explanation": "Pinned test documents substantiate this controlled outcome.",
            "quote_ids": {label: 0 for label in quotes}})}},
        mock_web_response={"nondet_web_request": {url: {"method": "GET", "status": 200, "body": body}
            for url, body in documents.items()}})
    return {"validators": [v.to_dict() for v in validators]}


def test_three_party_clearing_challenge_and_conservation():
    client, account = connect()
    actors = participants()
    filename = "integration-activity.json"
    if (ROOT / filename).exists():
        journal = json.loads((ROOT / filename).read_text())
        assert journal["network"] == "studionet" and journal["chain_id"] == 61999 and journal["mocked"]
    else:
        journal = {"network": "studionet", "chain_id": 61999, "mocked": True, "transactions": []}
        tx = client.deploy_contract(code=(ROOT / "contracts" / "loopforge.py").read_text(),
            args=["LoopForge controlled GenVM integration"], account=account, leader_only=False)
        journal["deploy_tx"] = str(tx)
        save(filename, journal)
    if "address" not in journal:
        journal["address"] = extract_contract_address(wait(client, journal["deploy_tx"]))
        save(filename, journal)
    address = journal["address"]
    import base64
    assert base64.b64decode(client.provider.make_request("gen_getContractCode", [address])["result"]) == \
        (ROOT / "contracts" / "loopforge.py").read_bytes()
    index = 0
    def send(actor, method, args, value=0, config=None, rejection=None):
        nonlocal index
        if index < len(journal["transactions"]):
            row = journal["transactions"][index]
            assert row["method"] == method and row["sender"].lower() == actor.address.lower()
            assert row["value_atto"] == str(value) and row["address"] == address
            if row["status"] not in ("accepted", "finalized"):
                receipt = wait(client, row["tx"], rejection, status=TransactionStatus.ACCEPTED)
                leader = receipt["consensus_data"]["leader_receipt"][0]
                row.update(status="finalized" if str(receipt["status"]) == "7" else "accepted", execution=leader["execution_result"],
                           result=leader.get("result"), expected_rejection=rejection)
                save(filename, journal)
            assert row["execution"] == "SUCCESS" if rejection is None else row["execution"] != "SUCCESS"
        else:
            write(client, actor, address, method, args, journal, filename,
                value=value, sim_config=config, rejection=rejection, wait_status=TransactionStatus.ACCEPTED)
        index += 1
    def state():
        p = read(client, address, "get_protocol")
        assert int(p["introduced_grams"]) == sum(int(p[k]) for k in
            ("available_grams", "reserved_grams", "receipt_grams", "unreconciled_grams", "retired_grams"))
        assert int(p["paid_in_atto"]) == sum(int(p[k]) for k in
            ("bond_escrow_atto", "claimable_atto", "withdrawn_atto"))
        return p
    documents = {}
    send(account, "set_source", [PREFIX, True])
    for i, actor in enumerate(actors):
        lot_name, need_name = "LOT-" + str(i), "NEED-" + str(i)
        url = PREFIX + COMMIT + "/lot" + str(i) + ".md"
        documents[url] = lot_name + ". " + SUPPLY
        send(actor, "create_lot", [lot_name, "polymer", 1000, SUPPLY, url, digest(documents[url])])
        url = PREFIX + COMMIT + "/need" + str(i) + ".md"
        documents[url] = need_name + ". " + NEED
        send(actor, "create_need", [need_name, "polymer", 1000, 1, NEED, url, digest(documents[url])])
    send(account, "propose_cycle", [[1, 2, 3], [2, 3, 1], [400] * 3, 17, 86400, 86400, 86400, "integration-cycle"])
    for leg in range(3):
        send(account, "review_fit", [1, leg], config=context(documents, "fit", "fit"))
    for actor in actors:
        send(actor, "approve_cycle", [1], value=17)
    send(account, "lock_cycle", [1])
    if index == len(journal["transactions"]):
        assert state()["reserved_grams"] == "1200"
    send(actors[1], "report_dispatch", [1, 0], rejection="dispatching supplier only")
    for leg, actor in enumerate(actors):
        send(actor, "report_dispatch", [1, leg])
        url = PREFIX + COMMIT + "/delivery" + str(leg) + ".md"
        documents[url] = DELIVERY
        send(actor, "submit_delivery", [1, leg, url, digest(documents[url])])
        send(account, "review_delivery", [1, leg], config=context(documents, "delivery", "conformant"))
    for actor in actors:
        send(actor, "consent_settlement", [1])
    url = PREFIX + COMMIT + "/new-inspection.md"
    documents[url] = DELIVERY + " Additional receiving inspection reconfirms specification."
    send(actors[1], "challenge_delivery", [1, 0, url, digest(documents[url]),
        "A new receiving inspection supplies additional evidence for the delivery."])
    cycle = read(client, address, "get_cycle", [1])
    if index == len(journal["transactions"]):
        assert cycle["settlement_consents"] == [False] * 3
    send(account, "settle_cycle", [1], rejection="receipt window or unanimous consent required")
    send(account, "review_delivery", [1, 0], config=context(documents, "delivery", "conformant"))
    for actor in actors:
        send(actor, "consent_settlement", [1])
    send(account, "settle_cycle", [1])
    if index == len(journal["transactions"]):
        assert state()["receipt_grams"] == "1200"
    assert read(client, address, "get_cycle", [1])["accepted_legs"] == 3
    send(account, "settle_cycle", [1], rejection="cycle not awaiting settlement")
    url = PREFIX + COMMIT + "/reused.md"
    documents[url] = "REUSED. " + SUPPLY
    send(actors[1], "create_received_lot", [1, "REUSED", 250, SUPPLY, url, digest(documents[url])])
    assert state()["introduced_grams"] == "3000"
    assert state()["receipt_grams"] == "950"
    send(account, "withdraw", [])
    finalize_journal(client, journal, filename)
    assert read(client, address, "get_claimable", [account.address]) == "0"
    journal["snapshot"] = state()
    journal["status"] = "controlled_genvm_cycle_verified"
    save(filename, journal)
