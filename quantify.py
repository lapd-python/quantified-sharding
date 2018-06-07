from web3 import Web3, HTTPProvider
import json

debug = False

# Geth node parameters
rpcport = '9111'

# Experiment parameters
numBuckets = 50

# Instantiate web3
web3 = Web3(HTTPProvider('http://localhost:' + rpcport))

# Iterate over blocks and print transactions
latest = web3.eth.getBlock('latest').number

# Data struct for results
addressBalances = {}
shardedChain = {}
counter = 0

# Current parameters
startBlock = 4400000
endBlock = 4400050

for curBlockNum in range(startBlock,endBlock):
	
	# Gets current block	
	currentBlock = web3.eth.getBlock(curBlockNum, full_transactions=True)
	print "+++++++ Current block: " + str(curBlockNum) + " +++++++++++"

	# Iterates through current block's transactions
	for txn in currentBlock.transactions:
		
		# fromAddress details	
		fromAddr = txn['from']
		fromAddrInitialBalance = web3.eth.getBalance(fromAddr, block_identifier=(startBlock-1))	
		
		toAddr = txn['to']
		txnValue = txn['value']

		if (debug):	
			print "	========= New Txn ========"
			print "	Current Block Num: " + str(curBlockNum)
			print "	from: " + fromAddr
			print "	from Address balance: " + str(web3.fromWei(fromAddrBal, 'ether'))
			print "	from Address balance before: " + str(web3.fromWei(fromAddrBalBefore, 'ether'))
			if (toAddr): print "	to: " + toAddr
			print "	txnValue: " + str(web3.fromWei(txnValue, 'ether'))
		counter+=1

print "Counter: " + str(counter)
