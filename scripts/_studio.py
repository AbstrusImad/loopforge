"""Explicit project credentials and StudioNet-only, finalized transaction handling."""
import json
import time
from collections import Counter
from pathlib import Path

from dotenv import dotenv_values
from genlayer_py import create_account, create_client
from genlayer_py.chains import studionet
from genlayer_py.exceptions import GenLayerError
from genlayer_py.types import TransactionHashVariant, TransactionStatus

ROOT = Path(__file__).resolve().parents[1]
RPC = "https://studio.genlayer.com/api"
CHAIN_ID = 61999
EXPECTED_ACCOUNT = "0x95803126315A05E642D8E46CE1d77eA2199a2A6E"
RUNNER = "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6"


def account_from(key):
    if not key:
        raise RuntimeError("Missing local signing configuration; populate the project .env")
    key = key.strip()
    return create_account(account_private_key=key if key.startswith("0x") else "0x" + key)


def connect(wallet_env=None):
    # A different environment file is used only when explicitly passed by the operator.
    values = dotenv_values(Path(wallet_env) if wallet_env else ROOT / ".env")
    account = account_from(values.get("private_key_wallet"))
    if account.address.lower() != EXPECTED_ACCOUNT.lower():
        raise RuntimeError("Deployer differs from the selected main_account address")
    if studionet.id != CHAIN_ID or studionet.rpc_urls["default"]["http"][0] != RPC:
        raise RuntimeError("StudioNet SDK configuration changed; refusing to sign")
    client = create_client(chain=studionet, account=account)
    original_request = client.provider.make_request
    next_request = 0.0
    def paced_request(method, params):
        nonlocal next_request
        time.sleep(max(0.0, next_request - time.monotonic()))
        try:
            return original_request(method, params)
        finally:
            next_request = time.monotonic() + 1.3
    client.provider.make_request = paced_request
    raw = client.provider.make_request("eth_chainId", [])["result"]
    remote = int(raw, 16) if isinstance(raw, str) and raw.startswith("0x") else int(raw)
    if remote != CHAIN_ID:
        raise RuntimeError("Endpoint does not report StudioNet chain 61999")
    return client, account


def participants():
    values = dotenv_values(ROOT / ".env")
    actors = [account_from(values.get(k)) for k in
              ("private_key_wallet", "participant_private_key_1", "participant_private_key_2")]
    if len({a.address.lower() for a in actors}) != 3:
        raise RuntimeError("A genuine three-party cycle requires three distinct signing accounts")
    return actors


def save(name, record):
    target = ROOT / name
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)


def retry_read(operation):
    """Retry temporary RPC outages for reads only; never repeat a signed send."""
    for attempt in range(8):
        try:
            return operation()
        except GenLayerError as exc:
            temporary = any(marker in str(exc) for marker in
                ("-32002", "-32429", "429", "Service temporarily unavailable",
                 "ConnectionPool", "Read timed out"))
            if not temporary or attempt == 7:
                raise
            print("Temporary StudioNet read failure; retrying the same request.", flush=True)
            time.sleep(min(5 * (attempt + 1), 20))


def wait(client, tx, rejection=None, status=TransactionStatus.FINALIZED):
    receipt = retry_read(lambda: client.wait_for_transaction_receipt(transaction_hash=tx,
        status=status, interval=5000 if status == TransactionStatus.ACCEPTED else 15000, retries=90))
    leaders = receipt.get("consensus_data", {}).get("leader_receipt") or []
    if not leaders:
        raise RuntimeError("Transaction has no execution receipt")
    leader = leaders[0]
    success = leader.get("execution_result") == "SUCCESS"
    result = leader.get("result", {})
    if rejection:
        if success or rejection not in str(result):
            raise RuntimeError("Expected policy rejection not established: " + str(result)[:800])
    elif not success:
        raise RuntimeError("Contract execution failed: " + str(result)[:1200])
    return receipt


def read(client, address, method, args=None, variant=TransactionHashVariant.LATEST_FINAL):
    return retry_read(lambda: client.read_contract(address=address, function_name=method, args=args or [],
        transaction_hash_variant=variant))


def write(client, account, address, method, args, journal, journal_name,
          value=0, sim_config=None, rejection=None, wait_status=TransactionStatus.FINALIZED):
    tx = client.write_contract(address=address, function_name=method, args=args,
        account=account, value=value, leader_only=False, sim_config=sim_config)
    row = {"tx": str(tx), "method": method, "address": address, "sender": account.address,
           "value_atto": str(value), "status": "submitted"}
    journal.setdefault("transactions", []).append(row)
    save(journal_name, journal)
    receipt = wait(client, tx, rejection, status=wait_status)
    leader = receipt["consensus_data"]["leader_receipt"][0]
    consensus = receipt["consensus_data"]
    votes = consensus.get("votes") or {}
    summary = {"validators_count": len(consensus.get("validators") or []),
               "leader_receipts_count": len(consensus.get("leader_receipt") or []),
               "vote_counts": dict(Counter(str(v) if type(v) in (str, int, bool)
                                           else "structured_vote" for v in votes.values()))}
    row.update({"status": "finalized" if str(receipt["status"]) == "7" else "accepted", "execution": leader["execution_result"],
                "expected_rejection": rejection, "result": leader.get("result"),
                "consensus_summary": summary})
    save(journal_name, journal)
    print(method + ": " + ("expected rejection verified" if rejection else "SUCCESS"), flush=True)
    return receipt


def finalize_journal(client, journal, filename):
    """Confirm every accepted outcome is finalized before claiming a run passed."""
    for row in journal["transactions"]:
        if row["status"] != "finalized":
            receipt = wait(client, row["tx"], row.get("expected_rejection"))
            leader = receipt["consensus_data"]["leader_receipt"][0]
            row.update(status="finalized", execution=leader["execution_result"], result=leader.get("result"))
            save(filename, journal)
    assert all(row["status"] == "finalized" for row in journal["transactions"])
