import json
from urllib.parse import urlparse
import requests
from multiprocessing import process
from itertools import repeat
import multiprocessing
import time

def mineBlockPoW(port):
    startTime = time.time()
    requests.get(f'http://localhost:{port}/PoW/mine')
    endTime = time.time()
    return endTime - startTime

def mineBlockPos(port):
    requests.post("http://localhost:5100/synchronise")
    startTime = time.time()
    for i in range(0,100):
        startMineTimer = time.time()
        requests.get(f'http://localhost:{port}/PoS/mine')
        endMineTimer = time.time()
        print(f"{i}:{endMineTimer - startMineTimer}")
        
    #response = requests.get(f'http://localhost:{port}/nodes/resolve')
    endTime = time.time()
    return endTime - startTime
    

def generateRequestJson(startPort,endPort):
    requestArray = []
    # Register everything
    for i in range(startPort,endPort):
        requestString = "http://localhost:" + str(i)
        requestArray.append(requestString)
    #payload = json.dumps({'nodes':requestArray})
    myjson = {'nodes':requestArray}
    return myjson

def registerPort(port,requestjson):
    response = requests.post(f'http://localhost:{port}/nodes/register', json=requestjson)
    walletJson = {'wallet':5}
    requests.post(f'http://localhost:{port}/wallet/set',json=walletJson)
    return response.status_code

def register(startPort, endPort):
    requestArray = []
    # Register everything
    for i in range(startPort,endPort):
        requestString = "http://localhost:" + str(i)
        requestArray.append(requestString)

    for i in range(startPort,endPort):
        #print(requestArray)
        payload = json.dumps({'nodes':requestArray})
        myjson = {'nodes':requestArray}
        #print(json.loads(payload))
        response = requests.post(f'http://localhost:{i}/nodes/register',json=myjson)

if __name__ == '__main__':
    from argparse import ArgumentParser 
    
    parser = ArgumentParser()
    parser.add_argument('-s', '--startPort', default=5100, type=int, help='first port registered')
    parser.add_argument('-e', '--endPort', default=5105, type=int, help='last port registered')
    parser.add_argument('-r', '--register', default=False, type=bool, help='set to true to register ports')
    args = parser.parse_args()
    startPort = args.startPort
    endPort = args.endPort
    shouldReg = args.register
    inputs = range(startPort,endPort)
    
    
    # multiprocessing pool object 
    pool = multiprocessing.Pool() 
  
    # pool object with number of element 
    pool = multiprocessing.Pool(processes=endPort-startPort) 
  
    if(shouldReg == True):
        jsonToReg = generateRequestJson(startPort,endPort)
        #register(startPort,endPort)
        outputs = pool.starmap(registerPort,zip(inputs,repeat(jsonToReg)))
        print("Register Outputs: {}".format(outputs))
    # map the function to the list and pass 
    # function and input list as arguments 
    algorithm = ""
    while(algorithm != "w" and algorithm != "s"):
        print("Please enter \"w\" to use PoW or \"s\" to use PoS")
        algorithm = input()
        if algorithm != "w" and algorithm != "s":
            print("invalid input")
    
    if algorithm == "w":
    #START POW
        total = 0
        for i in range(0,100):
            outputs = pool.map(mineBlockPoW, inputs)
            selected = 0
            fastestTime = 10000000000
            for j in range (0,len(outputs)):
                #print(outputs[i][-1][0])
                if(outputs[j] < fastestTime):
                    fastestTime = outputs[j]
                    selected = j
            startResolve = time.time()
            response = requests.get(f'http://localhost:{startPort}/nodes/resolve')
            endResolve = time.time()
            print(f"{i}:{fastestTime + endResolve - startResolve}")
            total = total + fastestTime + endResolve - startResolve
        print(f"total:{total}")
    # END POW
    
   
    if algorithm == "s":
    # START POS
        totalTime = mineBlockPos(startPort)
        print(f"total:{totalTime}")
    #END POS
    
    
    pool.close()
    
    