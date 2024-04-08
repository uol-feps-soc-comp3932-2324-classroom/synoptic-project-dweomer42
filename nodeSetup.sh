#!/bin/bash

for n in {5100..5200};
do
    python blockchain.py -p $n &
done