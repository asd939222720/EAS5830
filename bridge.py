from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware #Necessary for POA chains
from datetime import datetime
import json
import pandas as pd

WARDEN_PRIVATE_KEY = "0xd0a19f130a5477c1c4c6fefbd13d2da379a64887cbe325429257fdeb4e046cb6"

def connect_to(chain):
    if chain == 'source':  # The source contract chain is avax
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc" #AVAX C-chain testnet

    if chain == 'destination':  # The destination contract chain is bsc
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/" #BSC testnet

    if chain in ['source','destination']:
        w3 = Web3(Web3.HTTPProvider(api_url))
        # inject the poa compatibility middleware to the innermost layer
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def get_contract_info(chain, contract_info):
    """
        Load the contract_info file into a dictionary
        This function is used by the autograder and will likely be useful to you
    """
    try:
        with open(contract_info, 'r')  as f:
            contracts = json.load(f)
    except Exception as e:
        print( f"Failed to read contract info\nPlease contact your instructor\n{e}" )
        return 0
    return contracts[chain]

def build_contract(w3, info):
    addr = Web3.to_checksum_address(info["address"])
    abi = info["abi"]
    return w3.eth.contract(address=addr, abi=abi)


def send_tx(w3, fn):

    acct = w3.eth.account.from_key(WARDEN_PRIVATE_KEY)
    from_addr = acct.address
    chain_id = w3.eth.chain_id
    gas_price = w3.eth.gas_price

    try:
        gas_estimate = fn.estimate_gas({"from": from_addr})
    except Exception as e:
        print(f"Gas estimate failed, using fallback 500000: {e}")
        gas_estimate = 500000

    attempt = 0
    while attempt < 2:
        nonce = w3.eth.get_transaction_count(from_addr, "pending")

        tx = fn.build_transaction({
            "from": from_addr,
            "nonce": nonce,
            "chainId": chain_id,
            "gas": gas_estimate,
            "gasPrice": gas_price,
        })

        signed = w3.eth.account.sign_transaction(tx, private_key=WARDEN_PRIVATE_KEY)

        raw = getattr(signed, "rawTransaction", None)
        if raw is None:
            raw = getattr(signed, "raw_transaction", None)

        try:
            tx_hash = w3.eth.send_raw_transaction(raw)
            print(f"Sent tx: {tx_hash.hex()}")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"Tx mined in block {receipt.blockNumber}")
            return receipt
        except ValueError as e:
            msg = str(e)
            print(f"Error sending tx (attempt {attempt}): {msg}")

            if "nonce too low" in msg and attempt == 0:
                print("Nonce too low, retrying with updated nonce...")
                attempt += 1
                continue
            raise

    print("Failed to send transaction after retry.")
    return None


def scan_blocks(chain, contract_info="contract_info.json"):
    """
        chain - (string) should be either "source" or "destination"
        Scan the last 5 blocks of the source and destination chains
        Look for 'Deposit' events on the source chain and 'Unwrap' events on the destination chain
        When Deposit events are found on the source chain, call the 'wrap' function the destination chain
        When Unwrap events are found on the destination chain, call the 'withdraw' function on the source chain
    """

    # This is different from Bridge IV where chain was "avax" or "bsc"
    if chain not in ['source', 'destination']:
        print(f"Invalid chain: {chain}")
        return 0

    w3_source = connect_to("source")
    w3_dest = connect_to("destination")

    if w3_source is None or w3_dest is None:
        print("Failed to connect to one or both chains")
        return 0


    source_info = get_contract_info("source", contract_info)
    dest_info = get_contract_info("destination", contract_info)

    source_contract = build_contract(w3_source, source_info)
    dest_contract = build_contract(w3_dest, dest_info)

    if chain == "source":
        scan_w3 = w3_source
        scan_contract = source_contract
        event_name = "Deposit"

        target_w3 = w3_dest
        target_contract = dest_contract

    else:  # chain == "destination"
        scan_w3 = w3_dest
        scan_contract = dest_contract
        event_name = "Unwrap"

        target_w3 = w3_source
        target_contract = source_contract

    latest_block = scan_w3.eth.block_number

    if chain == "destination":
        WINDOW = 15
    else:
        WINDOW = 5

    from_block = max(latest_block - WINDOW + 1, 0)
    to_block = latest_block

    print(f"Scanning {chain} for {event_name} events from block {from_block} to {to_block}...")

    logs = []

    if event_name == "Deposit":
        try:
            EventClass = getattr(scan_contract.events, event_name)
        except AttributeError:
            print(f"Contract does not have event {event_name}")
            return 0

        try:
            logs = EventClass.get_logs(from_block=from_block, to_block=to_block)
        except Exception as e:
            print(f"Error fetching Deposit logs: {e}")
            return 0


    else:  

        topic0 = scan_w3.keccak(
            text="Unwrap(address,address,address,address,uint256)"
        ).hex()

        EventClass = scan_contract.events.Unwrap

        for blk in range(to_block, from_block - 1, -1):
            try:
                block = scan_w3.eth.get_block(blk)
            except Exception as e:
                print(f"Error getting block {blk}: {e}")
                continue

            try:
                raw_logs = scan_w3.eth.get_logs({
                    "blockHash": block["hash"],
                    "address": scan_contract.address,
                    "topics": [topic0],
                })
                if raw_logs:
                    for raw in raw_logs:
                        ev = EventClass().process_log(raw)
                        logs.append(ev)
                    break
            except Exception as e:
                print(f"Error fetching Unwrap logs for block {blk}: {e}")
                continue

    if not logs:
        print("No relevant events found.")
        return 0

    for ev in logs:
        args = ev["args"]
        print(f"Found {event_name} event: {args}")

        if event_name == "Deposit":

            token = args["token"]
            recipient = args["recipient"]
            amount = args["amount"]

            print(f"Calling wrap() on destination: token={token}, recipient={recipient}, amount={amount}")
            fn = target_contract.functions.wrap(token, recipient, amount)
            send_tx(target_w3, fn)

        elif event_name == "Unwrap":

            underlying = args["underlying_token"]
            to_addr = args["to"]
            amount = args["amount"]

            print(f"Calling withdraw() on source: token={underlying}, recipient={to_addr}, amount={amount}")
            fn = target_contract.functions.withdraw(underlying, to_addr, amount)
            send_tx(target_w3, fn)

    return 1
