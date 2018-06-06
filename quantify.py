from web3 import Web3, HTTPProvider
import json

# Geth node parameters
rpcport = '9111'

# Experiment parameters
numBuckets = 50

# Instantiate web3
web3 = Web3(HTTPProvider('http://localhost:' + rpcport))

# Iterate over blocks and print transactions
latest = web3.eth.getBlock('latest').number

for i in range(4400000, 4500000):
	currentBlock = web3.eth.getBlock(i, full_transactions=True)
	print currentBlock.transactions
