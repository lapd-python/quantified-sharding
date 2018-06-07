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
		addressBalances[addr] = [{ 
			'origBlock': startBlock-1, 
			'endBal': web3.eth.getBalance(addr, block_identifier=(startBlock-1)), 
			'epoch': 0,
			'txnType':"init"
		}]
	return addressBalances[addr][-1]['endBal']

for curBlockNum in range(startBlock,endBlock):
	
	# Gets current block	
	currentBlock = web3.eth.getBlock(curBlockNum, full_transactions=True)
	print "+++++++ Current block: " + str(curBlockNum) + " +++++++++++"

	# Iterates through current block's transactions
	for txn in currentBlock.transactions:
		
		# fromAddress details	
		fromAddr = txn['from']
		fromAddrInitialBalance = getInitialBalance(fromAddr)		
		
		# Shard
		shard = hash(fromAddr) % 50

		# toAddress details	
		toAddr = txn['to']
		if (toAddr): toAddrInitialBalance = getInitialBalance(toAddr)

		# txn details
		txnValue = txn['value']
		txnHash = txn['hash']

		# Get the last transaction involving fromAddress
		lastTxn = addressBalances[fromAddr][-1]
		txnEpoch = lastTxn['epoch']

		# Inserts internal transaction if new endBal is negative (see issue #17)
		# -- solution: add a 'internal' transaction 
		newFromAddrBal = fromAddrInitialBalance - txnValue
		if (newFromAddrBal < 0):
			fromAddrCurBlockEndingBal = web3.eth.getBalance(fromAddr, block_identifier=curBlockNum)
			addressBalances[fromAddr].append({
				'origBlock': curBlockNum-1, 	# default approximation
				'endBal': fromAddrCurBlockEndingBal + txnValue,
				'epoch': lastTxn['epoch']+1,	# default approximation (possible for internal transaction to be in same block)
				'txnType': 'internal',
				'txnValue': fromAddrCurBlockEndingBal - newFromAddrBal
			})
			
			newFromAddrBal = fromAddrCurBlockEndingBal
			txnEpoch += 2	# default approximation (internal transaction needs to settle first, before next transac)
		
		# if (toAddr): newToAddrBal = web3.eth.getBalance(toAddr, block_identifier=curBlockNum)
		if (toAddr): newToAddrBal = toAddrInitialBalance + txnValue
		if (newFromAddrBal < 0 or newToAddrBal < 0): debug = True

		# Get the last transaction involving fromAddress (TODO: refactor)
		lastTxn = addressBalances[fromAddr][-1]

		# Insert the current transaction addressBalances
		# if (fromAddr not in addressBalances):
		# 		addressBalances[fromAddr] = []
		addressBalances[fromAddr].append({ 
			'origBlock': curBlockNum, 
			'endBal': newFromAddrBal, 
			'epoch': txnEpoch,
			'txnType': "send",
			'txnValue': -txnValue
		})
		if (toAddr): addressBalances[toAddr].append({
			'origBlock': curBlockNum, 
			'endBal': newToAddrBal,
			'epoch': txnEpoch,
			'txnType': "receive",
			'txnValue': txnValue
		})

		if (debug):	
			print "	========= New Txn ========"
			print "	Current Block Num: " + str(curBlockNum)
			print "	from: " + fromAddr
			print "	from Address balance before: " + str(web3.fromWei(fromAddrInitialBalance, 'ether'))
			print pprint.pprint(addressBalances[fromAddr])
			print "	txnValue: " + str(web3.fromWei(txnValue, 'ether'))
			print "	from Address balance after: " + str(web3.fromWei(newFromAddrBal, 'ether'))
			if (toAddr): 
				print "	to: " + toAddr
				print "	to Address balance before: " + str(web3.fromWei(toAddrInitialBalance, 'ether'))
				print " to Address balance after: " + str(web3.fromWei(newToAddrBal, 'ether'))
		
		debug = False		

			

pprint.pprint(addressBalances)

