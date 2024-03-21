import hashlib
import json
from time import time
from flask import Flask, jsonify, request
from uuid import uuid4

class Blockchain():
  def init(self):
    self.chain = []
    self.currentTransactions = []

    self.createBlock(previousHash=1,proof=100)

  def createBlock(self,proof, previousHash=None):
    # Creates a block and adds it to the chain
    block = {
      'index': len(self.chain) + 1,
      'timestamp': time(),
      'proof': proof,
      'previousHash': previousHash or self.hash(self.chain[-1])
    }
    pass

  def newTransaction(self,sender,recipient,amount):
    # Adds a new transaction to the list of transactions
    self.current_transactions.append({
      'sender': sender,
      'recipient': recipient,
      'amount': amount,
    })
    return self.lastBlock['index'] + 1
  
  @staticmethod
  def proofOfWork(self, lastProof):
    proof = 0
    while self.validProof(lastProof, proof) is False:
      proof += 1

    return proof
  
  @staticmethod
  def validProof(lastProof, proof):
    guess = f'{lastProof}{proof}'.encode()
    hashedGuess = hashlib.sha256(guess).hexdigest()
    return hashedGuess

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

if __name__ == "__main__":
  app.run()

nodeId = str(uuid4()).replace('-', '')

blockchain = Blockchain()

# Calc PoW, add a transaction with 1 amount, add to chain
@app.route('/mine', methods=['GET'])
def mine():
    lastBlock = blockchain.lastBlock
    lastProof = lastBlock['proof']
    proof = blockchain.proofOfWork(lastProof)
    # Sender = 0 so we've done it, recipent is nodeId, so us, amount = 1
    blockchain.newTransaction("0",nodeId,1)
    
    previousHash = blockchain.__hash__(lastBlock)
    block = blockchain.newBlock(proof,previousHash)
    
    # Inform the caller that we forged a new block
    response = {
      'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
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
  
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)