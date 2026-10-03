"""Verify actual StudioNet GEN balances and reclaim all controlled-cycle bonds."""
import json
import time

from _studio import ROOT, connect, participants, read, save, wait, write

FILE = "native-balance-audit.json"


def main():
    client, account = connect()
    actors = participants()
    integration = json.loads((ROOT / "integration-activity.json").read_text())
    assert integration["status"] == "controlled_genvm_cycle_verified"
    address = integration["address"]
    path = ROOT / FILE
    if path.exists():
        journal = json.loads(path.read_text())
        assert journal["address"] == address and journal["network"] == "studionet"
    else:
        # The main signer has already withdrawn its 17 attoGEN in the integration
        # scenario. The remaining owners still have their own original deposits.
        for _ in range(20):
            before = [int(client.get_balance(a.address)) for a in actors]
            contract_balance = int(client.get_balance(address))
            if before[1:] == [983, 983] and contract_balance == 34:
                break
            time.sleep(2)
        assert before[1:] == [983, 983], before
        assert contract_balance == 34
        assert read(client, address, "get_protocol")["claimable_atto"] == "34"
        journal = {"network": "studionet", "chain_id": 61999, "address": address,
                   "actors": [a.address for a in actors], "before_atto": [str(v) for v in before],
                   "contract_before_atto": "34", "transactions": []}
        save(FILE, journal)
    for index, actor in enumerate(actors[1:]):
        if index < len(journal["transactions"]):
            row = journal["transactions"][index]
            if row["status"] != "finalized":
                receipt = wait(client, row["tx"])
                row.update(status="finalized", execution="SUCCESS")
                save(FILE, journal)
        else:
            assert read(client, address, "get_claimable", [actor.address]) == "17"
            write(client, actor, address, "withdraw", [], journal, FILE)
    # Native transfer effects may be indexed after the parent is finalized.
    for _ in range(30):
        after = [int(client.get_balance(a.address)) for a in actors]
        contract_balance = int(client.get_balance(address))
        if after[1:] == [1000, 1000] and contract_balance == 0:
            break
        time.sleep(2)
    assert after[1:] == [1000, 1000], after
    assert after[0] == int(journal["before_atto"][0]), after
    assert contract_balance == 0
    state = read(client, address, "get_protocol")
    assert state["paid_in_atto"] == state["withdrawn_atto"] == "51"
    assert state["claimable_atto"] == state["bond_escrow_atto"] == "0"
    assert read(client, address, "get_lot", [1])["available_grams"] == 600
    assert read(client, address, "get_need", [2])["fulfilled_grams"] == 400
    assert read(client, address, "get_receipt", [1])["unissued_grams"] == 150
    page = read(client, address, "list_cycles", [1, 32])
    assert len(page) == 1 and page[0]["phase"] == "settled"
    assert all(read(client, address, "get_claimable", [a.address]) == "0" for a in actors)
    if len(journal["transactions"]) == 2:
        write(client, account, address, "withdraw", [], journal, FILE, rejection="nothing claimable")
    elif journal["transactions"][2]["status"] != "finalized":
        row = journal["transactions"][2]
        receipt = wait(client, row["tx"], "nothing claimable")
        row.update(status="finalized", execution=receipt["consensus_data"]["leader_receipt"][0]["execution_result"])
    journal.update(status="actual_native_balance_changes_verified", after_atto=[str(v) for v in after],
                   contract_after_atto="0", protocol=state, all_seven_views_verified=True)
    save(FILE, journal)
    print("All 51 attoGEN actually returned; contract balance is zero; repeat withdrawal refused.", flush=True)


if __name__ == "__main__":
    main()
