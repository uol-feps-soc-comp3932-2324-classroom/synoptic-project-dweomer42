#!/bin/bash

for n in {5000..5005};
do
    python blockchain.py -p $n &
done