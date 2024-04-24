#!/bin/bash

for n in {5100..5105};
do
    python blockchain.py -p $n &
done