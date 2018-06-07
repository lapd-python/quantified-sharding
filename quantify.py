from web3 import Web3, HTTPProvider
import json
import pprint

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

# Function to getInitialBalance
def getInitialBalance(addr):
	if(addr not in addressBalances):
		addressBalances[addr] = [ [startBlock-1, web3.eth.getBalance(addr, block_identifier=(startBlock-1)), "init"] ]
	return addressBalances[addr][-1][1]

for curBlockNum in range(startBlock,endBlock):
	
	# Gets current block	
	currentBlock = web3.eth.getBlock(curBlockNum, full_transactions=True)
	print "+++++++ Current block: " + str(curBlockNum) + " +++++++++++"

	# Iterates through current block's transactions
	for txn in currentBlock.transactions:
		
		# fromAddress details	
		fromAddr = txn['from']
		fromAddrInitialBalance = getInitialBalance(fromAddr)		
	
		# toAddress details	
		toAddr = txn['to']
		if (toAddr): toAddrInitialBalance = getInitialBalance(toAddr)

		# txn details
		txnValue = txn['value']
		txnHash = txn['hash']

		# Insert the current transaction into the shardedChain and addressBalances
		if (fromAddr not in addressBalances):
			addressBalances[fromAddr] = []
		# create data struct to represent the current transaction
		# later, create struct to represent current epoch
		addressBalances[fromAddr].append([curBlockNum, fromAddrInitialBalance-txnValue, "send"])
		if (toAddr): addressBalances[toAddr].append([curBlockNum, toAddrInitialBalance+txnValue, "receive"])

		if (debug):	
			print "	========= New Txn ========"
			print "	Current Block Num: " + str(curBlockNum)
			print "	from: " + fromAddr
			print "	from Address balance before: " + str(web3.fromWei(fromAddrInitialBalance, 'ether'))
			if (toAddr): print "	to: " + toAddr
			print "	txnValue: " + str(web3.fromWei(txnValue, 'ether'))
			print txn		


print pprint.pprint(addressBalances)

