"""Review an existing cycle's pending fit legs with real StudioNet models and sources."""
import argparse
import json

from _studio import ROOT, connect, read, save, write


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cycle_id", type=int)
    options = parser.parse_args()
    client, account = connect()
    deployment = json.loads((ROOT / "deployment.json").read_text())
    if deployment.get("status") != "deployed" or deployment.get("network") != "studionet":
        raise RuntimeError("A verified StudioNet deployment is required")
    address = deployment["address"]
    path = ROOT / "default-model-reviews.json"
    journal = json.loads(path.read_text()) if path.exists() else {
        "network": "studionet", "chain_id": 61999, "mocked": False, "transactions": []}
    if journal.get("network") != "studionet" or journal.get("chain_id") != 61999:
        raise RuntimeError("Unexpected review journal network")
    if any(r["status"] != "finalized" for r in journal["transactions"]):
        raise RuntimeError("Inspect pending receipt before resuming; do not resubmit ambiguously")
    cycle = read(client, address, "get_cycle", [options.cycle_id])
    for leg in range(len(cycle["lots"])):
        current = read(client, address, "get_cycle", [options.cycle_id])
        if current["fits"][leg]["verdict"] == "pending":
            write(client, account, address, "review_fit", [options.cycle_id, leg],
                journal, "default-model-reviews.json")
    journal["snapshot"] = read(client, address, "get_cycle", [options.cycle_id])
    journal["status"] = "real_model_reviews_recorded"
    journal["all_legs_fit"] = all(r["verdict"] == "fit" for r in journal["snapshot"]["fits"])
    save("default-model-reviews.json", journal)
    print("All legs fit: " + str(journal["all_legs_fit"]))


if __name__ == "__main__":
    main()
