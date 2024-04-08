import json
from urllib.parse import urlparse
import requests
from multiprocessing import process
import multiprocessing
import time

def mineBlock(port):
    startTime = time.time()
    for i in range(0,100):
        requests.get(f'http://localhost:{port}/mine')
        #response = requests.get(f'http://localhost:{port}/nodes/resolve')
        
    response = requests.get(f'http://localhost:{port}/nodes/resolve')
    endTime = time.time()
    return endTime - startTime
    





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
    parser.add_argument('-s', '--startPort', default=5000, type=int, help='first port registered')
    parser.add_argument('-e', '--endPort', default=5005, type=int, help='last port registered')
    parser.add_argument('-r', '--register', default=False, type=bool, help='set to true to register ports')
    args = parser.parse_args()
    startPort = args.startPort
    endPort = args.endPort
    shouldReg = args.register
    if(shouldReg == True):
        register(startPort,endPort)
    # input list 
    inputs = range(startPort,endPort)
    
    # multiprocessing pool object 
    pool = multiprocessing.Pool() 
  
    # pool object with number of element 
    pool = multiprocessing.Pool(processes=endPort-startPort) 
  
    # map the function to the list and pass 
    # function and input list as arguments 
    outputs = pool.map(mineBlock, inputs)

    # Print output list 
    print("Output: {}".format(outputs))  
    