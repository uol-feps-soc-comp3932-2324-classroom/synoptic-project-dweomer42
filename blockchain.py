import hashlib
import json
from time import time
from flask import Flask, jsonify, request
from uuid import uuid4
from urllib.parse import urlparse
import requests

class Blockchain:
  def __init__(self):
    self.chain = []
    self.currentTransactions = []
    self.nodes = set()

    self.createBlock(previousHash=1,proof=100)

  def registerNode(self, address):
    parsedUrl = urlparse(address)
    self.nodes.add(parsedUrl.netloc)

  def createBlock(self,proof, previousHash=None):
    # Creates a block and adds it to the chain
    block = {
      'index': len(self.chain) + 1,
      'timestamp': time(),
      'transactions': self.currentTransactions,
      'proof': proof,
      'previousHash': previousHash or self.hash(self.chain[-1])
    }
    # Reset the current list of transactions
    self.currentTransactions = []
    
    # Add the block to our chain
    self.chain.append(block)
    
    return block

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
  def validProof(lastProof, proof):
    guess = f'{lastProof}{proof}'.encode()
    hashedGuess = hashlib.sha256(guess).hexdigest()
    return hashedGuess[:4] == "0000"
  
  def validChain(self, chain):
    lastBlock = chain[0]
    currentIndex = 1
    
    while currentIndex < len(chain):
      block = chain[currentIndex]
      print(f'{lastBlock}')
      print(f'{block}')
      print("\n-----------\n")
      
      if block['previousHash'] != self.__hash__(lastBlock):
        return False

      if not self.validProof(lastBlock['proof'], block['proof']):
        return False
      
      lastBlock = block
      currentIndex += 1
    return True

  def resolveConflicts(self):
    neighbours = self.nodes
    newChain = None
    
    maxLength = len(self.chain)
    
    for node in neighbours:
      response = requests.get(f'http://{node}/chain')
      if response.status_code == 200:
        length = response.json()['length']
        chain = response.json()['chain']
        
        if length > maxLength and self.validChain(chain):
          maxLength = length
          newChain = chain
    
    if newChain:
      self.chain = newChain
      return True
    
    return False
    

  @staticmethod
  def __hash__(block):
    # Hashes a block
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
  print(values)
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
@app.route("/mine", methods=['GET'])
def mine():
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
    }
    return jsonify(response) , 200
  
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
    
if __name__ == '__main__':
    from argparse import ArgumentParser 
    
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port
    app.run(host='0.0.0.0', port=port)