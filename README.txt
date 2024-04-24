To run a blockchain node, use "python blockchain.py -p {port}" to open a node on the given port

The nodeSetup.sh file can be run using "bash nodeSetup.sh" and will run 6 nodes from ports 5100 to 5105. 
This can be edited if a different number of nodes are required

The server.py file takes the following 2 parameters: 
-s starting port, should be set to the port of the first node running on your machine
-e ending port, should be set to 1 higher than the last node running on your machine

The server.py file allows you to select either PoW or PoS and will mine 100 blocks using the chosen consensus algorithm.
It will measure time taken to mine each block and print them to the terminal. 
To record results, this output can be redirected into a txt file as seen below:
python .\server.py -s 5100 -e 5201 > output.txt

