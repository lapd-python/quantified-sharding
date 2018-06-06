from web3 import Web3, HTTPProvider

# Geth node parameters
rpcport = '9111'

# Instantiate web3
web3 = Web3(HTTPProvider('http://localhost:' + rpcport))

# Testing code
print web3.eth.getBlock('latest').number
