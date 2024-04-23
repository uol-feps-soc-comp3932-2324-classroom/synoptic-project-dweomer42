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

class Blockchain:
  def __init__(self):
    self.chain = []
    self.currentTransactions = []
    self.nodes = set()
    self.wallet = 0
    self.validator = ""
    self.validatorTimeout = 0

    self.createBlock(previousHash=1,proof=100)

  def registerNode(self, address):
    parsedUrl = urlparse(address)
    self.nodes.add(parsedUrl.netloc)

  def createBlock(self,proof, previousHash=None):
    tree = MerkleTree(algorithm='sha256')
    for t in self.currentTransactions:
      tree.append_entry(json.dumps(t))
      
    root = tree.root
      
    if tree.root:
      root = tree.root.hex()
    
    # Creates a block and adds it to the chain
    block = {
      'index': len(self.chain) + 1,
      'timestamp': time(),
      'transactions': self.currentTransactions,
      'proof': proof,
      'previousHash': previousHash or self.hash(self.chain[-1]),
      'merkleRoot': root
    }
    # Reset the current list of transactions
    self.currentTransactions = []
    
    # Add the block to our chain
    self.chain.append(block)
    
    return block
  
  
  def createBlockPoS(self, previousHash=None):
    tree = MerkleTree(algorithm='sha256')
    for t in self.currentTransactions:
      tree.append_entry(json.dumps(t))
      
    root = tree.root
      
    if tree.root:
      root = tree.root.hex()
    
    # Creates a block and adds it to the chain
    block = {
      'index': len(self.chain) + 1,
      'timestamp': time(),
      'transactions': self.currentTransactions,
      'previousHash': previousHash or self.hash(self.chain[-1]),
      'merkleRoot': root
    }
    # Reset the current list of transactions
    self.currentTransactions = []
    
    # Add the block to our chain
    #self.chain.append(block)
    
    return block
  
  
  
  
  
  
  
  def setWallet(self, value):
    self.wallet = value
    

  def newTransaction(self,sender,recipient,amount):
    # Adds a new transaction to the list of transactions
    self.currentTransactions.append({
      'sender': sender,
      'recipient': recipient,
      'amount': amount,
    })
    return self.lastBlock['index'] + 1
  
  def getTransactions(self):
    return self.currentTransactions
  
  def proofOfWork(self, lastProof):
    proof = 0
    while self.validProof(lastProof, proof) is False:
      proof += 1

    return proof
  
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
  
  @staticmethod
  def validProof(lastProof, proof):
    guess = f'{lastProof}{proof}'.encode()
    hashedGuess = hashlib.sha256(guess).hexdigest()
    return hashedGuess[:5] == "00000"
  
  @staticmethod
  def getNodeWallet(node):
    response = requests.get("http://" + node + "/wallet/get")
    return {'value': response.json()['value'], 'node':node}
  

  def getAndValidateChain(self,node):
    response = requests.get(f'http://{node}/chain')
    if(self.validChain(response.json()['chain'])):
      return response
    return
  
  @staticmethod
  def sendValidatorToNode(node, validator):
    requestJson = {
      'validator':validator
    }
    response = requests.post("http://" + node + "/validator/update",json=requestJson)
    return response
  
  def transmitChain(self,node):
    requestJson = {
      'chain':self.chain
    }
    response = requests.post("http://" + node + "/replace",json=requestJson)
    return response
    
  
  def validChain(self, chain):
    lastBlock = chain[0]
    currentIndex = 1
    
    while currentIndex < len(chain):
      block = chain[currentIndex]

      
      if block['previousHash'] != self.__hash__(lastBlock):
        return False

      if not self.validProof(lastBlock['proof'], block['proof']):
        return False
      
      if self.checkMerkleRoot(block) == False:
        return False
      
      lastBlock = block
      currentIndex += 1
    return True

  def resolveConflicts(self):
    neighbours = self.nodes
    newChain = None
    
    maxLength = len(self.chain)
    
    pool = multiprocessing.Pool()
    allChains = pool.map(self.getAndValidateChain,neighbours)
    
    for response in allChains:
      if not response:
        continue
      if response.status_code == 200:
        length = response.json()['length']
        chain = response.json()['chain']
        
        if length > maxLength:
          maxLength = length
          newChain = chain
    
    if newChain:
      self.chain = newChain
    
    pool.map(self.transmitChain,blockchain.nodes)
    pool.close()
    
    return False
  
    

  @staticmethod
  def __hash__(block):
    # Hashes a block
    # if block['merkleRoot']:
    #   block['merkleRoot'] = block['merkleRoot'].hex()
    blockString = json.dumps(block, sort_keys=True).encode()
    return hashlib.sha256(blockString).hexdigest()

  @property
  def lastBlock(self):
    # Returns the last block in the chain
    return self.chain[-1]


app = Flask(__name__)

@app.route("/")
def hello():
  return "Hello World!"


nodeId = str(uuid4()).replace('-', '')

blockchain = Blockchain()


@app.route('/nodes/register', methods=['POST'])
def registerNodes():
  values = request.get_json()
  nodes = values.get('nodes')
  if nodes is None:
    return "Error: Please supply a valid list of nodes", 400
  
  for node in nodes:
    blockchain.registerNode(node)
    
  response = {
    'message' : 'New nodes have been added',
    'total_nodes' : list(blockchain.nodes)
  }
  
  return jsonify(response), 201

@app.route('/nodes/validator', methods=['GET'])
def selectValidator():
  threads = len(blockchain.nodes)
  pool = multiprocessing.Pool(processes=threads) 
  #blockchain.getNodeWallet(blockchain.nodes[0])
  outputs = pool.map(blockchain.getNodeWallet,blockchain.nodes)
  cumulativeValues = outputs
  for i in range(0,len(cumulativeValues) - 1):
    cumulativeValues[i+1]['value'] = cumulativeValues[i+1]['value'] + cumulativeValues[i]['value']
  selected = random.randint(0,cumulativeValues[-1]['value'])

  # initialise to the first value in the list
  nodeSelected = cumulativeValues[0]['node']
  
  # find the range between which the random sample lies
  for i in range(1,len(cumulativeValues)):
    # If it's larger than the previous but smaller than the current than it's within the current node's set
    if cumulativeValues[i - 1]['value'] < selected and cumulativeValues[i]['value'] > selected:
      nodeSelected = cumulativeValues[i]['node']
      break

  
  pool.starmap(blockchain.sendValidatorToNode,zip(blockchain.nodes,repeat(nodeSelected)))
  pool.close()
  #requests.post("http://" + nodeSelected + "/synchronise")
  #nodeSelected = list(blockchain.nodes)[chosenNodeIndex]
  return f"selected node {nodeSelected} with random number {selected}" , 200
  
@app.route('/validator/update', methods=['POST'])
def updateValidator():
  myJson = request.json
  newValidator = myJson['validator']
  blockchain.validator = newValidator
  blockchain.validatorTimeout = 5
  return "validator updated successfully", 200

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolveConflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200
  
  
# Calc PoW, add a transaction with 1 amount, add to chain
@app.route("/PoW/mine", methods=['GET'])
def minePoW():
    lastBlock = blockchain.lastBlock
    lastProof = lastBlock['proof']
    proof = blockchain.proofOfWork(lastProof)
    # Sender = 0 so we've done it, recipent is nodeId, so us, amount = 1
    blockchain.newTransaction("0",nodeId,1)
    
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
  if blockchain.validatorTimeout <= 0:
    selectValidator()
  lastBlock = blockchain.lastBlock
  #lastProof = lastBlock['proof']
  #proof = blockchain.proofOfWork(lastProof)
  # Sender = 0 so we've done it, recipent is nodeId, so us, amount = 1
  blockchain.newTransaction("0",nodeId,1)
  
  previousHash = blockchain.__hash__(lastBlock)
  block = blockchain.createBlockPoS(previousHash)
  requestJson = {'block':block}
  validBlockResponse = requests.get("http://" + blockchain.validator + "/validateBlock",json=requestJson)
  if validBlockResponse.status_code == 200:
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

@app.route('/validateBlock', methods=['GET'])
def PoSValidate():
  block = request.json['block']
  lastBlock = blockchain.chain[-1]


  if block['previousHash'] != blockchain.__hash__(lastBlock):
    return "invalid block parent hash, another node may have mined before", 400  
  if blockchain.checkMerkleRoot(block) == False:
    return "invalid block, Merkle root does not match block transactions", 400
  
  
  blockchain.chain.append(block)

  
  threads = len(blockchain.nodes)
  pool = multiprocessing.Pool(processes=threads) 
  #blockchain.getNodeWallet(blockchain.nodes[0])
  pool.map(blockchain.transmitChain,blockchain.nodes)
  pool.close()
  blockchain.wallet += 1
  
  return "Chain valid, transmitting across network", 200
  
@app.route('/transactions/new', methods=['POST'])
def newTransaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = blockchain.newTransaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201
  
@app.route('/chain', methods=['GET'])
def fullChain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200
  
@app.route('/synchronise', methods=['POST'])
def synchronise():
  threads = len(blockchain.nodes)
  pool = multiprocessing.Pool(processes=threads) 
  pool.map(blockchain.transmitChain,blockchain.nodes)
  pool.close()
  return "Synchronised successfully", 200
  
@app.route('/replace', methods=['POST'])
def replaceChain():
  response = request.get_json()
  newChain = response['chain']
  blockchain.chain = newChain
  blockchain.validatorTimeout -= 1
  return "Succesfully replaced chain", 200
  
@app.route('/transactions/pending', methods=['GET'])
def pendingTransactions():
  transactions = blockchain.getTransactions()
  response = {
    'transactions' : transactions
  }
  return jsonify(response), 200
  
@app.route('/blocks', methods=['GET'])
def countBlocks():
  response = {
    'length' : len(blockchain.chain)
  }
  return jsonify(response), 200

@app.route('/wallet/set', methods=['POST'])
def updateWalletValue():
  values = request.get_json()
  required = ['wallet']
  if not all(k in values for k in required):
        return 'Missing values', 400
  newWallet = values['wallet']
  blockchain.setWallet(newWallet) 
  response = {'message': f'Wallet value updated to new value {blockchain.wallet}'}
  return jsonify(response), 200

@app.route('/wallet/get', methods=['GET'])
def getWalletValue():
  response = {
    'value' : blockchain.wallet
  }
  return jsonify(response),200
  
  
  
    
if __name__ == '__main__':
    from argparse import ArgumentParser 
    
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port
    app.run(host='0.0.0.0', port=port)