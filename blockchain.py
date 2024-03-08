from flask import Flask

class Blockchain():
  def init(self):
    self.chain = []
    self.currentTransactions = []

  def createBlock(self):
    # Creates a block and adds it to the chain
    pass

  def newTransaction(self):
    # Adds a new transaction to the list of transactions
    pass

  @staticmethod
  def __hash__(self):
    # Hashes a block
    pass

  @property
  def lastBlock(self):
    # Returns the last block in the chain
    pass


app = Flask(__name__)

@app.route("/")
def hello():
  return "Hello World!"

if __name__ == "__main__":
  app.run()
