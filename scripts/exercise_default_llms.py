"""Public-evidence refusal test with real default StudioNet models, no mocks.

These are demonstration declarations backed by educational reference documents,
not authenticated physical lots. Such documents cannot prove batch cleanliness
or delivery. The test requires the protocol to block the incomplete cycle.
"""
import hashlib
import json

import requests

from genlayer_py.types import TransactionStatus, TransactionHashVariant
from _studio import ROOT, connect, participants, read as read_state, save, wait, write, finalize_journal


def read(client, address, method, args=None):
    return read_state(client, address, method, args, variant=TransactionHashVariant.LATEST_NONFINAL)

PREFIX = "https://raw.githubusercontent.com/ONEARMY/academy/"
COMMIT = "9e6fc1e75845b663add8e305a77d8f700f4732ac"
PATHS = ["docs/plastic/basics.md", "docs/build/shredderprorun.md",
         "docs/plastic/geeky.md", "docs/plastic/safety.md"]
FILE = "default-model-activity.json"


def main():
    client, account = connect()
    actors = participants()
    deployment = json.loads((ROOT / "deployment.json").read_text())
    assert deployment["network"] == "studionet" and deployment["status"] == "deployed"
    address = deployment["address"]
    session = requests.Session()
    session.trust_env = False
    docs = []
    for path in PATHS:
        url = PREFIX + COMMIT + "/" + path
        response = session.get(url, timeout=30)
        response.raise_for_status()
        assert len(response.content) <= 16384
        docs.append((url, hashlib.sha256(response.content).hexdigest()))
    names = ["PVC", "HDPE", "PET"]
    for name, path in zip(names, PATHS[:3]):
        response = session.get(PREFIX + COMMIT + "/" + path, timeout=30)
        response.raise_for_status()
        assert name in response.text
    filename = ROOT / FILE
    if filename.exists():
        journal = json.loads(filename.read_text())
        assert journal["address"] == address and journal["network"] == "studionet"
    else:
        state = read(client, address, "get_protocol")
        assert state["lots"] == state["needs"] == state["cycles"] == 0
        journal = {"network": "studionet", "chain_id": 61999, "address": address,
                   "mocked": False, "leader_only": False, "public_evidence_commit": COMMIT,
                   "scenario": "Reference documents do not prove physical batches; incompatible or incomplete legs must block consent.",
                   "sources": [{"url": u, "sha256": h} for u, h in docs], "transactions": []}
        save(FILE, journal)
    # Every signed step is journaled before polling. Resume finalized steps instead
    # of creating duplicate records or rerolling already cached semantic decisions.
    def step(actor, method, args, rejection=None):
        nonlocal index
        if index < len(journal["transactions"]):
            row = journal["transactions"][index]
            assert row["method"] == method and row["sender"].lower() == actor.address.lower()
            if row["status"] not in ("accepted", "finalized"):
                receipt = wait(client, row["tx"], rejection, status=TransactionStatus.ACCEPTED)
                leader = receipt["consensus_data"]["leader_receipt"][0]
                row.update(status="finalized" if str(receipt["status"]) == "7" else "accepted", execution=leader["execution_result"],
                           result=leader.get("result"), expected_rejection=rejection)
                save(FILE, journal)
        else:
            write(client, actor, address, method, args, journal, FILE, rejection=rejection,
                  wait_status=TransactionStatus.ACCEPTED)
        index += 1
    index = 0
    step(account, "set_source", [PREFIX, True])
    for actor, name, (url, digest) in zip(actors, names, docs[:3]):
        step(actor, "create_lot", [name, "polymer", 1000,
             "Demonstration " + name + " declaration using public reference information; no batch measurements or contamination certificate supplied.", url, digest])
        step(actor, "create_need", ["Precious Plastic", "polymer", 1000, 1,
             "Precious Plastic machine processing: accept only suitable sorted clean single-polymer material; reject PVC. Require evidence for actual batch cleanliness, additives, and applicable operating precautions.",
             docs[3][0], docs[3][1]])
    step(account, "propose_cycle", [[1, 2, 3], [2, 3, 1], [400] * 3, 17,
         86400, 86400, 86400, "public-reference-blocking-cycle"])
    for leg in range(3):
        step(account, "review_fit", [1, leg])
    cycle = read(client, address, "get_cycle", [1])
    for decision in cycle["fits"]:
        assert decision["reason"] == "semantic_review", decision
        assert decision["verdict"] in ("no_fit", "uncertain"), decision
    journal["review_snapshot"] = cycle
    save(FILE, journal)
    step(account, "approve_cycle", [1], rejection="every material leg must fit")
    step(account, "lock_cycle", [1], rejection="unanimous bonded fit required")
    step(account, "revoke_consent", [1], rejection="no revocable draft consent")
    assert read(client, address, "get_protocol")["bond_escrow_atto"] == "0"
    step(account, "cancel_cycle", [1])
    for i, actor in enumerate(actors, 1):
        step(actor, "retire_lot", [i])
        step(actor, "retire_need", [i])
    finalize_journal(client, journal, FILE)
    state = read(client, address, "get_protocol")
    assert state["introduced_grams"] == state["retired_grams"] == "3000"
    assert state["reserved_grams"] == state["paid_in_atto"] == "0"
    journal.update(status="real_default_model_blocking_cycle_verified", snapshot=state,
                   final_cycle=read(client, address, "get_cycle", [1]))
    save(FILE, journal)
    print("Real default-model cycle safely blocked and cleaned up.", flush=True)


if __name__ == "__main__":
    main()
