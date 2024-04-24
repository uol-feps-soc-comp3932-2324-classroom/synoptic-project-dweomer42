import json
from urllib.parse import urlparse
import requests
from multiprocessing import process
from itertools import repeat
import multiprocessing
import time

# This function is used to mine a single block on a specific port
# It is used in parallel to run the blockchain using PoW
def mineBlockPoW(port):
    # Start block mining timer
    startTime = time.time()
    # Mine a block using PoW
    requests.get(f'http://localhost:{port}/PoW/mine')
    # End block mining timer
    endTime = time.time()
    # Return the time taken
    return endTime - startTime

# This function is used to mine a block using PoS
# It only needs to be run in serial since there is no need for blocks to race with this method
def mineBlockPos(startPort,port):
    # We first need to synchronise our chain so that each genesis block has the same timestamp
    requests.post(f"http://localhost:{port}/synchronise")
    # Start total timer
    startTime = time.time()
    # We mine 100 blocks 
    for i in range(0,100):
        # Start block mining timer
        startMineTimer = time.time()
        # Mine a block using PoS
        requests.get(f'http://localhost:{port}/PoS/mine')
        # End block mining timer
        endMineTimer = time.time()
        # Print the time taken
        print(f"{i}:{endMineTimer - startMineTimer}")
    # End total timer
    endTime = time.time()
    # We return the total time taken to mine 100 blocks
    return endTime - startTime
    
# This function is used to add all the ports we will use on our network to a json string so we can send them to be registered
def generateRequestJson(startPort,endPort):
    requestArray = []
    # Register everything
    for i in range(startPort,endPort):
        # Add the node address to the array
        requestString = "http://localhost:" + str(i)
        requestArray.append(requestString)
    # Convert the array to json so we can send it
    myjson = {'nodes':requestArray}
    return myjson

# This function is used to register all nodes on the network with a specific port
# It is used in parallel to ensure all nodes are aware of each other
def registerPort(port,requestjson):
    # We send a register request with our json payload to the node
    response = requests.post(f'http://localhost:{port}/nodes/register', json=requestjson)
    # We also set the node's wallet to 5 to help set up PoS
    walletJson = {'wallet':5}
    requests.post(f'http://localhost:{port}/wallet/set',json=walletJson)
    return response.status_code


if __name__ == '__main__':
    from argparse import ArgumentParser 
    
    # We parse the start and end port to ensure that we can connect up our entire network
    parser = ArgumentParser()
    parser.add_argument('-s', '--startPort', default=5100, type=int, help='first port registered')
    parser.add_argument('-e', '--endPort', default=5106, type=int, help='last port registered')
    args = parser.parse_args()
    startPort = args.startPort
    endPort = args.endPort
    inputs = range(startPort,endPort)
    
    
    # multiprocessing pool object 
    pool = multiprocessing.Pool() 
  
    # pool object with number of element 
    pool = multiprocessing.Pool(processes=endPort-startPort) 
    
    # We generate the request json to register our nodes
    jsonToReg = generateRequestJson(startPort,endPort)
    
    # We send register requests to each node in parallel
    outputs = pool.starmap(registerPort,zip(inputs,repeat(jsonToReg)))
    # If every result is 200 then every node was successfully registered with every other one
    print("Register Outputs: {}".format(outputs))
    
    # We make the user choose which algorithm they want to test so that we know which to get results for
    algorithm = ""
    while(algorithm != "w" and algorithm != "s"):
        print("Please enter \"w\" to use PoW or \"s\" to use PoS")
        algorithm = input()
        if algorithm != "w" and algorithm != "s":
            print("invalid input")
    
    if algorithm == "w":
        # START POW
        # We initialise our total time to 0 
        total = 0
        
        # We want to mine 100 blocks
        for i in range(0,100):
            # We try to mine a block on 100 nodes in parallel
            outputs = pool.map(mineBlockPoW, inputs)
            # We need to figure out which node finished mining the fastest, so that we can say how long it took to mine a block
            selected = 0
            fastestTime = 10000000000
            # We check each node to determine which finished the fastest
            for j in range (0,len(outputs)):
                if(outputs[j] < fastestTime):
                    fastestTime = outputs[j]
                    selected = j
            # We also start timing how long it takes to decide the authoritative node
            startResolve = time.time()
            # We resolve which node has the longest chain/is authoritative
            response = requests.get(f'http://localhost:{startPort}/nodes/resolve')
            # We end our timer for the decision
            endResolve = time.time()
            # We print the total time taken to mine a block and resolve all the chains
            print(f"{i}:{fastestTime + endResolve - startResolve}")
            # We also add the time taken to our total
            total = total + fastestTime + endResolve - startResolve
        # When we finish we print the total time taken to mine and resolve all 100 blocks
        print(f"total:{total}")
        # END POW
    
   
    if algorithm == "s":
        # START POS
        # We start mining all 100 blocks on a specific node and return time taken
        totalTime = mineBlockPos(startPort)
        # We print our total time taken to mine all 100 blocks
        print(f"total:{totalTime}")
        #END POS
    
    
    pool.close()
    
    