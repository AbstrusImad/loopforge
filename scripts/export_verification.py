"""Export allowlisted, secret-free proof of the completed StudioNet runs."""
import json
from datetime import datetime, timezone

from _studio import ROOT


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def main():
    deployment = load("deployment.json")
    integration = load("integration-activity.json")
    native = load("native-balance-audit.json")
    real = load("default-model-activity.json")
    funding = load("test-funding.json")
    assert deployment["status"] == "deployed" and deployment["live_source_matches"]
    assert integration["status"] == "controlled_genvm_cycle_verified"
    assert native["status"] == "actual_native_balance_changes_verified"
    assert real["status"] == "real_default_model_blocking_cycle_verified"
    def clean(journal):
        rows = []
        for row in journal["transactions"]:
            assert row["status"] == "finalized"
            rows.append({key: row[key] for key in
                ("tx", "method", "address", "sender", "value_atto", "status",
                 "execution", "expected_rejection", "consensus_summary") if key in row})
        return rows
    controlled_rows, native_rows, real_rows = map(clean, (integration, native, real))
    report = {"verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "network": "studionet", "chain_id": 61999, "rpc": "https://studio.genlayer.com/api",
        "main_contract": {key: deployment[key] for key in
            ("address", "deploy_tx", "deployer", "source_sha256", "live_source_sha256", "live_source_matches", "live_schema_methods")},
        "controlled_contract": {"address": integration["address"], "deploy_tx": integration["deploy_tx"],
            "model_and_web_mocks": True, "transactions": controlled_rows, "final_state": integration["snapshot"]},
        "native_balance_audit": {"transactions": native_rows, "actors": native["actors"],
            "before_atto": native["before_atto"], "after_atto": native["after_atto"],
            "contract_before_atto": native["contract_before_atto"], "contract_after_atto": native["contract_after_atto"],
            "all_seven_views_verified": native["all_seven_views_verified"], "final_state": native["protocol"]},
        "real_default_models": {"model_and_web_mocks": False, "leader_only": False,
            "transactions": real_rows, "sources": real["sources"],
            "fit_verdicts": [{key: decision[key] for key in ("verdict", "reason", "evidence_hashes")}
                for decision in real["review_snapshot"]["fits"]], "final_state": real["snapshot"],
            "physical_delivery_claimed": False},
        "test_wallet_funding": funding,
        "totals": {"finalized_contract_writes": len(controlled_rows) + len(native_rows) + len(real_rows),
            "successful_contract_writes": sum(row["execution"] == "SUCCESS" for row in controlled_rows + native_rows + real_rows),
            "expected_refusals": sum(bool(row.get("expected_rejection")) for row in controlled_rows + native_rows + real_rows),
            "deployments": 2, "test_funding_transfers": len(funding["transfers"])}}
    target = ROOT / "evidence" / "verification.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["totals"]))


if __name__ == "__main__":
    main()
