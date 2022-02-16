
# BoostCLI

[![Tests](https://github.com/valcanobacon/BoostCLI/actions/workflows/ci.yml/badge.svg)](https://github.com/valcanobacon/BoostCLI/actions/workflows/ci.yml)

## Requirements

* Python `3.9+`
* setuptools (tested with `57.4.0`)
* A Raspiblitz Node (LNPay Support Coming)

## Commands

### Send a Boost

![boostcli-send-boost-gif](/boost.gif)

### List Received Boosts

![boostcli-list-received-boosts-gif](/boosts-received-list.gif)

## Quick Start

### Terminal #1

Open a Tunnel from this computer to your Raspiblitz Node. Replace `192.168.1.100` with the IP Address of your node.

```sh
ssh -NL 10009:127.0.0.1:10009 admin@192.168.1.100
```

Enter your password when prompted and leave the terminal open.  Switch to a new terminal to continue the quick start.

### Terminal #2

#### Get Macaroon and TLS Certificate

Get the `readonly.macaroon` and `tls.cert` from your node

* SSH into Node, replace `192.168.1.100` with the IP Address of your node.  

    ```sh
    ssh admin@192.168.1.100 
    ```

* In Raspiblitz CONNECT -> EXPORT -> scp and following the instructions

#### Install Dependencies

This should be done in the directory that contains this project.

```sh
python3 -m venv venv && source venv/bin/activate # Optional but Recommended
pip install -e .
```

#### Read the docs

```sh
boostcli --help
boostcli boosts-received-list --help
```

#### Run Command

```sh
boostcli --tlscert tls.cert --macaroon readonly.macaroon --address 127.0.0.1 --port 10009 boosts-received-list --datetime-range-end 2021-10-26
```

```
2021-10-29 12:59:26 +1 Chat from='abcdefghijklmnopqrstuvwxyz' message='Hello From ThunderHub'
2021-10-28 23:06:58 +1320 Boosted amount='1333' app='Fountain' from='@adam' to='Podcaster' podcast='Test Podcast' episode='The first test' at='00:01' message='Hello World'
2021-10-28 23:01:18 +94 Boosted amount='100' app='Breez' podcast='Test Podcast' episode='The second test' at='00:00:01'
2021-10-28 22:46:04 +5245 Streamed
2021-10-28 22:43:01 +327 Streamed
```

## Virtual Environment Explained

Using a Python Virtual Environment is optional but highly recommended and is standard practice with development. The basic idea is you create a virtual environment for each project and install all the dependencies into it. The Virtual Environment only needs to be created once but must be activated everytime a new terminal is opened.

### Create Virtual Environment

```sh
python3 -m venv venv
```

### Activate Environment

```sh
source venv/bin/activate
```

### Deactive Environment

```sh
deactivate
```

## Sending a Boostagram with lncli

```sh
PUBKEY="03ecb3ee55ba6324d40bea174de096dc9134cb35d990235723b37ae9b5c49f4f53"
VALUE=69
MVALUE=$(expr $VALUE \* 1000)
SENDER_NAME="Dude named Ben"
MESSAGE="Test Message from lncli!"
RECEIVER_NAME="Podcaster"
APP_NAME="lncli"
DATA="{\"action\":\"boost\",\"value_msat_total\":\"$MVALUE\",\"app_name\":\"$APP_NAME\",\"sender_name\": \"$SENDER_NAME\",\"name\":\"$RECEIVER_NAME\",\"message\":\"$MESSAGE\"}"
RECORD=`echo $DATA |  od -A n -t x1 | sed -z 's/[ \n]*//g'`
lncli sendpayment --dest=$PUBKEY --amt=$VALUE --keysend --data 7629169=$RECORD
```

## Receive Boostagrams with lncli

```
for x in $(lncli listinvoices | jq '.invoices[].htlcs[0].custom_records."7629169"'); do echo $x | sed 's/"//g' | xxd -r -p; done
```
