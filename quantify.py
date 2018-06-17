from web3 import Web3, HTTPProvider
import json
import pprint
import requests

# Debug flags
debug_transaction = False
debug_CALL_transactions = False

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
addressTransactionLogs = {}
shardedChain = {}
counter = 0

# Current parameters
startBlock = 4400000
endBlock = 4400010
maxShardSize = 50

# Opcodes to monitor
monitoredOpcodes = [
	'CREATE', 
	'CALL', 
	'SLOAD',
	'SSTORE', 
	'CALLCODE', 
	'DELEGATECALL', 
	'SUICIDE', 
	'SELFDESTRUCT'
]
	
# Function to getInitialBalance
def getInitialBalance(addr):
	if(addr not in addressTransactionLogs):
		addressBal = web3.eth.getBalance(addr, block_identifier=(startBlock-1))
		addressTransactionLogs[addr] = [{ 
			'origBlock': startBlock-1, 
			'startBal': addressBal,
			'endBal': addressBal,
			'shard': -1,
			'epoch': 0,
			'txnType':"init"
		}]
	return addressTransactionLogs[addr][-1]['endBal']

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

		lastTxn = addressTransactionLogs[fromAddr][-1]

		txnEpoch = lastTxn['epoch']

		newFromAddrBal = fromAddrInitialBalance - txnValue
		if (toAddr): newToAddrBal = toAddrInitialBalance + txnValue
	
		# Sanity check for 
		if (newFromAddrBal < 0 or newToAddrBal < 0): debug_transaction = True

		# Get the last transaction involving fromAddress (TODO: refactor)
		lastTxn = addressTransactionLogs[fromAddr][-1]
		
		# shard
		addToShardedChain(txnEpoch, shard, txnHash)

		# Insert the current transaction addressTransactionLogs
		# if (fromAddr not in addressTransactionLogs):
		# 		addressTransactionLogs[fromAddr] = []
		addressTransactionLogs[fromAddr].append({ 
			'origBlock': curBlockNum, 
			'startBal': fromAddrInitialBalance,
			'endBal': newFromAddrBal, 
			'epoch': txnEpoch,
			'shard': shard,
			'txnType': "send",
			'txnValue': -txnValue
		})
		if (toAddr): addressTransactionLogs[toAddr].append({
			'origBlock': curBlockNum, 
			'startBal': toAddrInitialBalance,
			'endBal': newToAddrBal,
			'epoch': txnEpoch,
			'shard': shard,
			'txnType': "receive",
			'txnValue': txnValue
		})
	
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
				
				if(log['op'] == 'CALL'):
					txnGas = int(log['stack'][-1], 16)
					internalFromAddr = toAddr
					internalToAddr = '0x' + log['stack'][-2][24:64]	# Turn 64 char string into formatted address TODO: refactor into helper methhod
					internalTxnValue = int(log['stack'][-3], 16)
						
					internalFromAddrInitialBalance = getInitialBalance(internalFromAddr) + txnValue # Note: We add txnValue to cover instances where contract is a "pass through" contract
					internalToAddrInitialBalance = getInitialBalance(internalToAddr)	
					
					# TODO: Placeholder for addressTransactionLogs append
					addressTransactionLogs[internalFromAddr].append({ 
						'origBlock': curBlockNum, 
						'startBal': internalFromAddrInitialBalance,
						'endBal': internalFromAddrInitialBalance - internalTxnValue, 
						'epoch': txnEpoch, # TODO: Replace with epoch-pushing algorithm
						'shard': shard,
						'txnType': "internal-send",
						'txnValue': -internalTxnValue
					})
					addressTransactionLogs[internalToAddr].append({
						'origBlock': curBlockNum, 
						'startBal': internalToAddrInitialBalance,
						'endBal': internalToAddrInitialBalance + internalTxnValue,
						'epoch': txnEpoch, # TODO: replace with epoch-pushing algorithm
						'shard': shard,
						'txnType': "internal-receive",
						'txnValue': internalTxnValue
					})

					# Sanity check for internal transactions
					if (internalFromAddrInitialBalance < internalTxnValue): 
						debug_CALL_transactions = True	
						debug_transaction = True	

					if (debug_CALL_transactions):	
						print "====== Hash: " + txnHash
						print "TxnGas: " + str(txnGas)
						print "Internal fromAddr: " + internalFromAddr
						print "Internal toAddr: " + internalToAddr
						print "Internal txnValue: " + str(web3.fromWei(internalTxnValue, 'ether'))
						debug_CALL_transactions = False

		if (debug_transaction):	
			print "	========= New Txn ========"
			print "	Current Block Num: " + str(curBlockNum)
			print "	from: " + fromAddr
			print "	from Address balance before: " + str(web3.fromWei(fromAddrInitialBalance, 'ether'))
			print pprint.pprint(addressTransactionLogs[fromAddr])
			print "	txnValue: " + str(web3.fromWei(txnValue, 'ether'))
			print "	from Address balance after: " + str(web3.fromWei(newFromAddrBal, 'ether'))
			if (toAddr): 
				print "	to: " + toAddr
				print "	to Address balance before: " + str(web3.fromWei(toAddrInitialBalance, 'ether'))
				print " to Address balance after: " + str(web3.fromWei(newToAddrBal, 'ether'))
		
		debug_transaction = False		

# Get statistics
def shardSize(epochShards):
	return { shard: len(txnArr) for shard, txnArr in epochShards.items() }

shardedChainStats = { epoch: shardSize(epochShards) for epoch, epochShards in shardedChain.items() }

pprint.pprint(addressTransactionLogs)
pprint.pprint(shardedChainStats)
