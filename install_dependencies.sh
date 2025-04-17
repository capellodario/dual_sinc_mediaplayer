#!/bin/bash

echo "Aggiornamento della lista dei pacchetti..."
sudo apt update

echo "Installazione di python3-netifaces..."
sudo apt install -y python3-netifaces

echo "Dipendenza python3-netifaces installata!"



exit 0
