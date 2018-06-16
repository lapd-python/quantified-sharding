from web3 import Web3, HTTPProvider
import json
import pprint
import requests

debug = False

# Geth node parameters
rpcport = '9111'

# Experiment parameters
numBuckets = 50

# Instantiate web3
web3 = Web3(HTTPProvider('http://localhost:' + rpcport))
# Instantiate HTTP connection to Geth JSONRPC
session = requests.Session()

# Iterate over blocks and print transactions
latest = web3.eth.getBlock('latest').number

# Data struct for results
addressBalances = {}
shardedChain = {}
counter = 0

# Current parameters
startBlock = 4400000
endBlock = 4400050
maxShardSize = 50

# Opcodes to monitor
monitoredOpcodes = ['CREATE', 'CALL', 'SLOAD', 'SSTORE', 'CALLCODE', 'DELEGATECALL', 'SUICIDE', 'SELFDESTRUCT']
	
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

def addToShardedChain(txnEpoch, shard, txnHash):
	if(txnEpoch not in shardedChain): shardedChain[txnEpoch] = {}
	if (shard not in shardedChain[txnEpoch]): shardedChain[txnEpoch][shard] = []
	
	# Move to next epoch if epochShard is full
	currentShardSize = len(shardedChain[txnEpoch][shard])
	if (currentShardSize >= maxShardSize): 
		addToShardedChain(txnEpoch+1, shard, txnHash)
	else:
		shardedChain[txnEpoch][shard].append(txnHash)

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
	
		# Gets EVM Trace from debug_traceTransaction	
		params = [txnHash]
		payload = {
			"jsonrpc":"2.0",
			"method":"debug_traceTransaction",
			"params":params,
			"id":1
		}
		headers = {'Content-type':'application/json'}
		debugTraceTransaction = session.post(
			'http://localhost:'+rpcport, 
			json=payload, 
			headers=headers
		)
		transactionTrace = debugTraceTransaction.json()['result']['structLogs']

		# Handler for different EVM Opcodes
		if (transactionTrace):
			for log in transactionTrace:
				#if(log['op'] in monitoredOpcodes):
				if(log['op'] == 'CALL'):
					print "====== Hash: " + txnHash
					txnGas = int(log['stack'][-1], 16)
					internalFromAddr = toAddr
					internalToAddr = log['stack'][-2]
					internalTxnValue = int(log['stack'][-3], 16)
					print "TxnGas: " + str(txnGas)
					print "Internal fromAddr: " + internalFromAddr
					print "Internal toAddr: " + internalToAddr
					print "Internal txnValue: " + str(web3.fromWei(internalTxnValue, 'ether'))
						
						
							
		# Inserts internal transaction if new endBal is negative (see issue #17)
		# -- solution: add a 'internal' transaction 
		newFromAddrBal = fromAddrInitialBalance - txnValue
		if (newFromAddrBal < 0):
			fromAddrCurBlockEndingBal = web3.eth.getBalance(fromAddr, block_identifier=curBlockNum)
			txnEpoch += 1	# default approximation (internal transaction should be in new block)
			addressBalances[fromAddr].append({
				'origBlock': curBlockNum-1, 	# default approximation
				'endBal': fromAddrCurBlockEndingBal + txnValue,
				'epoch': txnEpoch,
				'txnType': 'internal',
				'txnValue': fromAddrCurBlockEndingBal - newFromAddrBal
			})
			addToShardedChain(txnEpoch, shard, '0xInternal')
			
			newFromAddrBal = fromAddrCurBlockEndingBal
			txnEpoch += 1	# default approximation (internal transaction needs to settle first, before next transac)
		
		if (toAddr): newToAddrBal = toAddrInitialBalance + txnValue
		if (newFromAddrBal < 0 or newToAddrBal < 0): debug = True

		# Get the last transaction involving fromAddress (TODO: refactor)
		lastTxn = addressBalances[fromAddr][-1]
		
		# shard
		addToShardedChain(txnEpoch, shard, txnHash)

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

# Get statistics
def shardSize(epochShards):
	return { shard: len(txnArr) for shard, txnArr in epochShards.items() }

shardedChainStats = { epoch: shardSize(epochShards) for epoch, epochShards in shardedChain.items() }

pprint.pprint(shardedChainStats)

