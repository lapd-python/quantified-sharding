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

for curBlockNum in range(4400000,4500000):
	currentBlock = web3.eth.getBlock(curBlockNum, full_transactions=True)
	print "+++++++ Current block: " + str(curBlockNum) + " +++++++++++"
	for txn in currentBlock.transactions:
		fromAddr = txn['from']
		toAddr = txn['to']
		txnValue = txn['value']
		fromAddrBal = web3.eth.getBalance(fromAddr, block_identifier=curBlockNum)
		fromAddrBalBefore = web3.eth.getBalance(fromAddr, block_identifier=(curBlockNum-1))	

		if (txnValue > fromAddrBalBefore):
			print "========= New Txn ========"
			print "Current Block Num: " + str(curBlockNum)
			print "from: " + fromAddr
			print "from Address balance: " + str(web3.fromWei(fromAddrBal, 'ether'))
			print "from Address balance before: " + str(web3.fromWei(fromAddrBalBefore, 'ether'))
			if (toAddr): print "to: " + toAddr
			print "txnValue: " + str(web3.fromWei(txnValue, 'ether'))

