import random
import json
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.providers.rpc import HTTPProvider


# If you use one of the suggested infrastructure providers, the url will be of the form
# now_url  = f"https://eth.nownodes.io/{now_token}"
# alchemy_url = f"https://eth-mainnet.alchemyapi.io/v2/{alchemy_token}"
# infura_url = f"https://mainnet.infura.io/v3/{infura_token}"

def connect_to_eth():
	url = "https://mainnet.infura.io/v3/9d2f8fac9d8946389aea3967385271c9"  # FILL THIS IN
	w3 = Web3(HTTPProvider(url))
	assert w3.is_connected(), f"Failed to connect to provider at {url}"
	return w3



def connect_with_middleware(contract_json):
	with open(contract_json, "r") as f:
		d = json.load(f)
		d = d['bsc']
		address = d['address']
		abi = d['abi']

	urlbnb = "https://bsc-testnet.infura.io/v3/9d2f8fac9d8946389aea3967385271c9"
	
	w3 = Web3(HTTPProvider(urlbnb))
	assert w3.is_connected(), f"Failed to connect to provider at {urlbnb}"
	
	# The second section requires you to inject middleware into your w3 object and
	# create a contract object. Read more on the docs pages at https://web3py.readthedocs.io/en/stable/middleware.html
	# and https://web3py.readthedocs.io/en/stable/web3.contract.html

	w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
	checksummed = Web3.to_checksum_address(address)
	contract = w3.eth.contract(address=checksummed, abi=abi)
	return w3, contract

def is_ordered_block(w3, block_num):
	"""
	Takes a block number
	Returns a boolean that tells whether all the transactions in the block are ordered by priority fee

	Before EIP-1559, a block is ordered if and only if all transactions are sorted in decreasing order of the gasPrice field

	After EIP-1559, there are two types of transactions
		*Type 0* The priority fee is tx.gasPrice - block.baseFeePerGas
		*Type 2* The priority fee is min( tx.maxPriorityFeePerGas, tx.maxFeePerGas - block.baseFeePerGas )

	Conveniently, most type 2 transactions set the gasPrice field to be min( tx.maxPriorityFeePerGas + block.baseFeePerGas, tx.maxFeePerGas )
	"""
	block = w3.eth.get_block(block_num, full_transactions=True)
	ordered = False

	txs = block.get("transactions", []) or []

	if len(txs) <= 1:
		return True
	
	

	def to_int(x):
		if x is None:
			return None
		if isinstance(x, int):
			return x
		if isinstance(x, str) and x.startswith("0x"):
			return int(x, 16)
		return int(x)
	
	
	base_fee = block.get("baseFeePerGas")
	base_fee = to_int(base_fee) if base_fee is not None else None
	
	transOrder = []

	for tx in txs:
		ttype =  tx_type(tx.get('type'))
		gas_price = to_int(tx.get('gasPrice'))

		if gas_price is None:
			mf = to_int(tx.get("maxFeePerGas"))
			mp = to_int(tx.get("maxPriorityFeePerGas"))
			if mf is not None and mp is not None and base_fee is not None:
				gas_price = min(mf, mp + base_fee)
			else:
				gas_price = 0
		transOrder.append(gas_price)

	if len(transOrder)>1:
		ordered = all(transOrder[i]>=transOrder[i+1] for i in range(len(transOrder)-1))
	return ordered


def get_contract_values(contract, admin_address, owner_address):
	"""
	Takes a contract object, and two addresses (as strings) to be used for calling
	the contract to check current on chain values.
	The provided "default_admin_role" is the correctly formatted solidity default
	admin value to use when checking with the contract
	To complete this method you need to make three calls to the contract to get:
	  onchain_root: Get and return the merkleRoot from the provided contract
	  has_role: Verify that the address "admin_address" has the role "default_admin_role" return True/False
	  prime: Call the contract to get and return the prime owned by "owner_address"

	check on available contract functions and transactions on the block explorer at
	https://testnet.bscscan.com/address/0xaA7CAaDA823300D18D3c43f65569a47e78220073
	"""
	default_admin_role = int.to_bytes(0, 32, byteorder="big")

	# TODO complete the following lines by performing contract calls

	admin = Web3.to_checksum_address(admin_address)
	owner = Web3.to_checksum_address(owner_address)
	onchain_root =contract.functions.merkleRoot().call()  # Get and return the merkleRoot from the provided contract
	has_role =contract.functions.hasRole(default_admin_role, admin).call()  # Check the contract to see if the address "admin_address" has the role "default_admin_role"
	prime = contract.functions.getPrimeByOwner(owner).call()  # Call the contract to get the prime owned by "owner_address"

	return onchain_root, has_role, prime


"""
	This might be useful for testing (main is not run by the grader feel free to change 
	this code anyway that is helpful)
"""
if __name__ == "__main__":
	# These are addresses associated with the Merkle contract (check on contract
	# functions and transactions on the block explorer at
	# https://testnet.bscscan.com/address/0xaA7CAaDA823300D18D3c43f65569a47e78220073
	admin_address = "0xAC55e7d73A792fE1A9e051BDF4A010c33962809A"
	owner_address = "0x793A37a85964D96ACD6368777c7C7050F05b11dE"
	contract_file = "contract_info.json"

	eth_w3 = connect_to_eth()
	cont_w3, contract = connect_with_middleware(contract_file)

	latest_block = eth_w3.eth.get_block_number()
	london_hard_fork_block_num = 12965000
	assert latest_block > london_hard_fork_block_num, f"Error: the chain never got past the London Hard Fork"

	n = 5
	for _ in range(n):
		block_num = random.randint(1, latest_block)
		ordered = is_ordered_block(block_num)
		if ordered:
			print(f"Block {block_num} is ordered")
		else:
			print(f"Block {block_num} is not ordered")
