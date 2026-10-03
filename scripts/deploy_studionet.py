"""Resume or deploy the atomic clearing contract to StudioNet only."""
import argparse
import hashlib
import json

from gltest.utils import extract_contract_address
from _studio import ROOT, RUNNER, RPC, CHAIN_ID, connect, read, save, wait


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wallet-env", help="Explicit local credential file; default is this project's .env")
    options = parser.parse_args()
    client, account = connect(options.wallet_env)
    source = (ROOT / "contracts" / "loopforge.py").read_text(encoding="utf-8")
    digest = hashlib.sha256(source.encode()).hexdigest()
    path = ROOT / "deployment.json"
    if path.exists():
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["network"] != "studionet" or record["chain_id"] != CHAIN_ID or \
           record["deployer"].lower() != account.address.lower() or record["source_sha256"] != digest:
            raise RuntimeError("Deployment journal differs from selected network, wallet or source")
    else:
        record = {"network": "studionet", "chain_id": CHAIN_ID, "rpc": RPC, "runner": RUNNER,
            "deployer": account.address, "source_sha256": digest, "status": "deploying"}
        tx = client.deploy_contract(code=source, account=account,
            args=["LoopForge StudioNet Clearing"], leader_only=False)
        record["deploy_tx"] = str(tx)
        save("deployment.json", record)
    if "address" not in record:
        receipt = wait(client, record["deploy_tx"])
        record["address"] = extract_contract_address(receipt)
        record["execution"] = "SUCCESS"
        save("deployment.json", record)
    record["verified_state"] = read(client, record["address"], "get_protocol")
    record["status"] = "deployed"
    save("deployment.json", record)
    print("LoopForge: " + record["address"])
    print("https://explorer-studio.genlayer.com/address/" + record["address"])


if __name__ == "__main__":
    main()
