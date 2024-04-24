import hashlib
import json
from time import time
from flask import Flask, jsonify, request
from uuid import uuid4
from urllib.parse import urlparse
from multiprocessing import process
from itertools import repeat
from pymerkle import MerkleTree
import multiprocessing
import requests
import random
from numba import jit

class Blockchain:
  # Initialise the blockchain 
  def __init__(self):
    self.chain = []
    self.currentTransactions = []
    self.nodes = set()
    self.wallet = 0
    self.validator = ""
    self.validatorTimeout = 0

    # Adds the genesis block to the chain
    self.createBlock(previousHash=1,proof=100)

  # When a node address is registered, it is parsed and added to the set of neighbour nodes
  def registerNode(self, address):
    parsedUrl = urlparse(address)
    self.nodes.add(parsedUrl.netloc)

  # Block creation function for PoW
  def createBlock(self,proof, previousHash=None):
    # Generating a Merkle Tree using the transactions currently stored on the node to store on the block
    tree = MerkleTree(algorithm='sha256')
    for t in self.currentTransactions:
      tree.append_entry(json.dumps(t))
      
    root = tree.root
      
    if tree.root:
      root = tree.root.hex()
    
    # Creates a block using the transactions currently stored on the node
    block = {
      'index': len(self.chain) + 1,
      'timestamp': time(),
      'transactions': self.currentTransactions,
      'proof': proof,
      'previousHash': previousHash or self.hash(self.chain[-1]),
      'merkleRoot': root
    }
    # Empties the list of transactions on the node
    self.currentTransactions = []
    
    # Add the block to our chain
    self.chain.append(block)
    
    return block
  
  # Block creation function for PoS
  def createBlockPoS(self, previousHash=None):
    # Generating a Merkle Tree using the transactions currently stored on the node to store on the block
    tree = MerkleTree(algorithm='sha256')
    for t in self.currentTransactions:
      tree.append_entry(json.dumps(t))
      
    root = tree.root
      
    if tree.root:
      root = tree.root.hex()
    
    # Creates a block using the transactions currently stored on the node
    # No proof is included as we don't need to "prove work" to make a block
    block = {
      'index': len(self.chain) + 1,
      'timestamp': time(),
      'transactions': self.currentTransactions,
      'previousHash': previousHash or self.hash(self.chain[-1]),
      'merkleRoot': root
    }
    # We don't automatically add the block to our chain like in PoW so we can't get rid of transactions on it until it is accepted
    
    return block
  
  # Helper function to allow us to add nodes with stake in the chain
  # If we could work out who mined/validated a block after it had been forged we could remove this to improve security
  def setWallet(self, value):
    self.wallet = value
    
  # Adds a new transaction to the ones stored on this node
  # They aren't immutable until forged into a block
  def newTransaction(self,sender,recipient,amount):
    self.currentTransactions.append({
      'sender': sender,
      'recipient': recipient,
      'amount': amount,
    })
    # Return the new transaction so we know it was successful
    return self.lastBlock['index'] + 1
  
  # A helper function to allow for testing that the node stores transactions correctly
  def getTransactions(self):
    return self.currentTransactions
  
  # Use of the Numba jit decorator allows us to run this code on the GPU
  #@jit
  # Our puzzle solver for PoW
  def proofOfWork(self, lastProof):
    proof = 0
    # Checks every value until it finds a valid solution
    while self.validProof(lastProof, proof) is False:
      proof += 1

    return proof
  
  # Function used to calculate the next validator for the network in PoS
  @staticmethod
  def calculateValidator(cumulativeValues):
    
    # Calculate the ranges for which each node is selected
    for i in range(0,len(cumulativeValues) - 1):
      cumulativeValues[i+1]['value'] = cumulativeValues[i+1]['value'] + cumulativeValues[i]['value']
      
    # Selects a random value up the the total wallet value of the network
    # It is weighted more towards nodes with greater wallet value since they represent a greater quantity of the total space
    selected = random.randint(0,cumulativeValues[-1]['value'])

    # Initialise to the first value in the list
    nodeSelected = cumulativeValues[0]['node']
  
    # Find the range between which the random sample lies
    for i in range(1,len(cumulativeValues)):
      # If it's larger than the previous value but smaller than the current than it's within the current node's set
      if cumulativeValues[i - 1]['value'] < selected and cumulativeValues[i]['value'] > selected:
        nodeSelected = cumulativeValues[i]['node']
        # Calculations stop after the correct node is found to avoid unnecessary work in larger networks
        break
    return nodeSelected
  
  # Checks the Merkle root of a block is calculated correctly as a form of validation
  # Uses the MerkleTree defined in the pymerkle library
  @staticmethod
  def checkMerkleRoot(block):
    transactionList = block['transactions']
    tree = MerkleTree(algorithm='sha256')
    for transaction in transactionList:
      tree.append_entry(json.dumps(transaction))
    root = block['merkleRoot']
    if root == tree.root.hex():
      return True
    return False
  
  # Our puzzle for PoW, the last proof must combine with the new solution to produce a string that starts with '00000'
  # Changing the number of 0's will change the puzzle difficulty accordingly
  @staticmethod
  #@jit
  def validProof(lastProof, proof):
    guess = f'{lastProof}{proof}'.encode()
    hashedGuess = hashlib.sha256(guess).hexdigest()
    return hashedGuess[:5] == "00000"
  
  # Gets the value of a given node's wallet
  # Used to help choose validators in PoS
  @staticmethod
  def getNodeWallet(node):
    response = requests.get("http://" + node + "/wallet/get")
    return {'value': response.json()['value'], 'node':node}
  
  # Gets the chain from a given node and validates it before returning it
  # This function allows us to validate chains in parallel to speed up the consensus process in PoW
  def getAndValidateChain(self,node):
    response = requests.get(f'http://{node}/chain')
    if(self.validChain(response.json()['chain'])):
      return response
    return
  
  # Informs another node that a new validator has been chosen
  # Used in parallel to transmit the validator to the whole network in PoS
  @staticmethod
  def sendValidatorToNode(node, validator):
    requestJson = {
      'validator':validator
    }
    response = requests.post("http://" + node + "/validator/update",json=requestJson)
    return response
  
  # Transmits this node's chain to another node
  # Used in parallel to replace all other chains on the network
  def transmitChain(self,node):
    requestJson = {
      'chain':self.chain
    }
    response = requests.post("http://" + node + "/replace",json=requestJson)
    return response
    
  # Checks if a given chain is valid for PoW
  #@jit
  def validChain(self, chain):
    # Assumes that the genesis block is valid since it starts the chain
    lastBlock = chain[0]
    currentIndex = 1
    
    # Iterates over the chain checking each block
    # If any block isn't valid then the entire chain is rejected
    while currentIndex < len(chain):
      block = chain[currentIndex]

      # If the "previous hash" doesn't point to the parent then the block isn't valid
      if block['previousHash'] != self.__hash__(lastBlock):
        return False
      
      # If the solution to our PoW puzzle is not correct then the block isn't valid
      if not self.validProof(lastBlock['proof'], block['proof']):
        return False
      
      # If the merkle root isn't calculated correctly then the block isn't valid
      if self.checkMerkleRoot(block) == False:
        return False
      
      lastBlock = block
      currentIndex += 1
    return True

  # Used to check every chain on the network to determine which is authoritative in PoW
  #@jit
  def resolveConflicts(self):
    neighbours = self.nodes
    # We assume at first that our chain is the longest or joint longest on the network
    newChain = None
    
    maxLength = len(self.chain)
    
    # We use parallel processing to get every other chain on the network and check that it is valid
    pool = multiprocessing.Pool()
    allChains = pool.map(self.getAndValidateChain,neighbours)
    
    for response in allChains:
      # We discard chains that weren't valid
      if not response:
        continue
      # For valid chains we check whether they are longer than our current chain
      if response.status_code == 200:
        length = response.json()['length']
        chain = response.json()['chain']
        
        # If the chain is longer, it will replace our current longest chain
        if length > maxLength:
          maxLength = length
          newChain = chain
    
    # If we found a longer chain it replaces our current one
    if newChain:
      self.chain = newChain
    
    # We transmit the longest chain across the network as our authoritative chain
    pool.map(self.transmitChain,blockchain.nodes)
    pool.close()
    
    return False
  
    

  # Hashes a block using SHA-256
  @staticmethod
  #@jit
  def __hash__(block):
    blockString = json.dumps(block, sort_keys=True).encode()
    return hashlib.sha256(blockString).hexdigest()

  # Returns the last block in the chain
  @property
  def lastBlock(self):
    return self.chain[-1]

# We set up our Flask app so we can communicate with our blockchain via API calls
app = Flask(__name__)


nodeId = str(uuid4()).replace('-', '')

# We initialise our blockchain on this node
blockchain = Blockchain()

@app.route('/nodes/register', methods=['POST'])
def registerNodes():
  # When we are asked to register nodes, we first check for nodes in the request json
  values = request.get_json()
  nodes = values.get('nodes')
  if nodes is None:
    return "Error: Please supply a valid list of nodes", 400
  
  # If we find nodes, we register each one
  for node in nodes:
    blockchain.registerNode(node)
    
  # We reply with the list of added nodes
  response = {
    'message' : 'New nodes have been added',
    'total_nodes' : list(blockchain.nodes)
  }
  
  return jsonify(response), 201

@app.route('/nodes/validator', methods=['GET'])
def selectValidator():
  # When asked to select a new validator we get the wallet value of each node in parallel
  threads = len(blockchain.nodes)
  pool = multiprocessing.Pool(processes=threads) 
  outputs = pool.map(blockchain.getNodeWallet,blockchain.nodes)
  
  # Using the returned values we decide on a validator
  nodeSelected = blockchain.calculateValidator(outputs)
  
  # We transmit our chosen validator to each node in parallel
  pool.starmap(blockchain.sendValidatorToNode,zip(blockchain.nodes,repeat(nodeSelected)))
  pool.close()
  return f"selected node {nodeSelected}" , 200
  
@app.route('/validator/update', methods=['POST'])
def updateValidator():
  # We read the request json
  myJson = request.json
  newValidator = myJson['validator']
  # We update our validator and set it to timeout after it has validated 5 blocks
  blockchain.validator = newValidator
  blockchain.validatorTimeout = 5
  return "validator updated successfully", 200

# Consensus for PoW
@app.route('/nodes/resolve', methods=['GET'])
def consensus():
  # We check for a longer chain on the network
  replaced = blockchain.resolveConflicts()

  # If we found a longer chain we communicate that we replaced ours
  if replaced:
    response = {
        'message': 'Our chain was replaced',
        'new_chain': blockchain.chain
        }
  # Otherwise we are the authoritative chain
  else:
    response = {
        'message': 'Our chain is authoritative',
        'chain': blockchain.chain
        }

  return jsonify(response), 200
  
  
# We calculate PoW, add a transaction with 1 amount and then add it to our chain
@app.route("/PoW/mine", methods=['GET'])
def minePoW():
  # We find the last block on the chain so we can calculate PoW
  lastBlock = blockchain.lastBlock
  lastProof = lastBlock['proof']
  proof = blockchain.proofOfWork(lastProof)
  
  # We add a transaction to our node so that we always have a transaction on our block
  # Sender = 0 so we've done it, recipent is nodeId, so us, amount = 1
  blockchain.newTransaction("0",nodeId,1)
  
  # We hash our last block and then create a new one
  previousHash = blockchain.__hash__(lastBlock)
  block = blockchain.createBlock(proof,previousHash)
    
  # Inform the caller that we forged a new block
  response = {
    'message': "New Block Forged",
      'index': block['index'],
      'transactions': block['transactions'],
      'proof': block['proof'],
      'previous_hash': block['previousHash'],
      'merkleRoot': block['merkleRoot']
  }
  return jsonify(response) , 200
  
@app.route("/PoS/mine", methods=['GET'])
def minePoS():
  # If our validator has timed out, we first select a new validator
  if blockchain.validatorTimeout <= 0:
    selectValidator()
  # We find the last block on our chain so our new block can point to it's parent block
  lastBlock = blockchain.lastBlock
  
  # We add a transaction to our node so that we always have a transaction on our block
  # Sender = 0 so we've done it, recipent is nodeId, so us, amount = 1
  blockchain.newTransaction("0",nodeId,1)
  
  # We hash our last block and then create a new one
  previousHash = blockchain.__hash__(lastBlock)
  block = blockchain.createBlockPoS(previousHash)
  
  # We send our newly generated block to our validator
  requestJson = {'block':block}
  validBlockResponse = requests.get("http://" + blockchain.validator + "/validateBlock",json=requestJson)
  if validBlockResponse.status_code == 200:
    # Empty the list of transactions on the node since our block has been accepted
    blockchain.currentTransactions = []
    # Inform the caller that we forged a new block
    response = {
      'message': "New Block Forged",
      'index': block['index'],
      'transactions': block['transactions'],
      'previous_hash': block['previousHash'],
      'merkleRoot': block['merkleRoot']
    } 
    return jsonify(response) , 200
  else:
    return "Unable to forge block, please try again", 400

# Our validator attempts to validate any blocks generated in PoS before they can be added to a chain
@app.route('/validateBlock', methods=['GET'])
def PoSValidate():
  
  # We first get the block sent in the request json
  block = request.json['block']
  
  # We then get the last block in our chain so we can validate that the new block has been calculated correctly
  lastBlock = blockchain.chain[-1]

  # We check the Merkle Root and Parent hash of the new block are valid for our chain
  # This does allow for a race condition, since two blocks may be sent at the same time and only one can be accepted
  if block['previousHash'] != blockchain.__hash__(lastBlock):
    return "invalid block parent hash, another node may have mined before", 400  
  if blockchain.checkMerkleRoot(block) == False:
    return "invalid block, Merkle root does not match block transactions", 400
  
  # If the block sent is valid, it is added to the validator's chain
  blockchain.chain.append(block)

  # We transmit our chain to each other node on the network in parallel
  threads = len(blockchain.nodes)
  pool = multiprocessing.Pool(processes=threads) 
  pool.map(blockchain.transmitChain,blockchain.nodes)
  pool.close()
  # The validator also has it's wallet increased by 1 as a reward for successfully validating a block
  blockchain.wallet += 1
  
  return "Chain valid, transmitting across network", 200
  
@app.route('/transactions/new', methods=['POST'])
def newTransaction():
  values = request.get_json()

  # Check that the required fields are in the POST'ed data
  required = ['sender', 'recipient', 'amount']
  if not all(k in values for k in required):
      return 'Missing values', 400

  # Create a new Transaction with the received values
  index = blockchain.newTransaction(values['sender'], values['recipient'], values['amount'])

  # We don't actually add this transaction to a block until a new one is forged
  # This just indicates which block will be forged next for it to be added to
  response = {'message': f'Transaction will be added to Block {index}'}
  return jsonify(response), 201

# When asked, we send a HTTP response containing this node's blockchain
@app.route('/chain', methods=['GET'])
def fullChain():
  response = {
      'chain': blockchain.chain,
      'length': len(blockchain.chain),
  }
  return jsonify(response), 200
  
# Synchronises all nodes to match this one - Needed for PoS to ensure genesis blocks share the same timestamp
@app.route('/synchronise', methods=['POST'])
def synchronise():
  # We transmit our chain to each other node in parallel
  threads = len(blockchain.nodes)
  pool = multiprocessing.Pool(processes=threads) 
  pool.map(blockchain.transmitChain,blockchain.nodes)
  pool.close()
  return "Synchronised successfully", 200
  
# We use this method to replace this node's chain with one that is sent
# This lets us receive updated chains that are transmitted across the network
@app.route('/replace', methods=['POST'])
def replaceChain():
  # We get the chain from the POST'ed json data
  response = request.get_json()
  newChain = response['chain']
  # We replace our chain with the new one
  blockchain.chain = newChain
  
  # We also tick down our validator timeout, indicating that we have received a validated block from it
  blockchain.validatorTimeout -= 1
  return "Succesfully replaced chain", 200
  
# This is a testing function to ensure that transactions are saved correctly onto a node
@app.route('/transactions/pending', methods=['GET'])
def pendingTransactions():
  transactions = blockchain.getTransactions()
  response = {
    'transactions' : transactions
  }
  return jsonify(response), 200
  
# This is another testing function to ensure that blockchain length is being calculated correctly
@app.route('/blocks', methods=['GET'])
def countBlocks():
  response = {
    'length' : len(blockchain.chain)
  }
  return jsonify(response), 200

# This function is used to set an initial value for this node's wallet
# It is a security vulnerability as it makes 51% attacks very easy but is used in testing to ensure nodes are included when calculating a validator
@app.route('/wallet/set', methods=['POST'])
def updateWalletValue():
  # We first get the Post'ed data and check that it includes what we need
  values = request.get_json()
  required = ['wallet']
  if not all(k in values for k in required):
        return 'Missing values', 400
  # We update the value of our wallet and communicate that to the sender
  newWallet = values['wallet']
  blockchain.setWallet(newWallet) 
  response = {'message': f'Wallet value updated to new value {blockchain.wallet}'}
  return jsonify(response), 200

# This is used when deciding a validator to ensure that other nodes can get our wallet value
@app.route('/wallet/get', methods=['GET'])
def getWalletValue():
  response = {
    'value' : blockchain.wallet
  }
  return jsonify(response),200
  
  
  
# We set the default port for a node and ensure that a node can have it's port set when spun up
# This allows us to have multiple nodes running on one machine for testing purposes
if __name__ == '__main__':
  from argparse import ArgumentParser 
    
  parser = ArgumentParser()
  parser.add_argument('-p', '--port', default=5100, type=int, help='port to listen on')
  args = parser.parse_args()
  port = args.port
  app.run(host='0.0.0.0', port=port)