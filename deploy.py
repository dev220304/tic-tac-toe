import boto3

region = "ap-south-1"
ec2 = boto3.client('ec2', region_name=region)

key_name = "tictactoe-key"

# 🔹 Create Key Pair
try:
    key = ec2.create_key_pair(KeyName=key_name)
    with open(f"{key_name}.pem", "w") as f:
        f.write(key['KeyMaterial'])
    print("✅ Key created")
except:
    print("⚠️ Key already exists")

# 🔹 Create Security Group
try:
    sg = ec2.create_security_group(
        GroupName='tictactoe-sg',
        Description='Allow SSH & HTTP'
    )
    sg_id = sg['GroupId']

    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {'IpProtocol':'tcp','FromPort':22,'ToPort':22,'IpRanges':[{'CidrIp':'0.0.0.0/0'}]},
            {'IpProtocol':'tcp','FromPort':80,'ToPort':80,'IpRanges':[{'CidrIp':'0.0.0.0/0'}]}
        ]
    )
    print("✅ SG created")
except:
    sg_id = ec2.describe_security_groups(GroupNames=['tictactoe-sg'])['SecurityGroups'][0]['GroupId']
    print("⚠️ Using existing SG")

# 🔹 USER DATA (FULL APP DEPLOY)
user_data = """#!/bin/bash
apt update -y
apt install apache2 python3-pip libapache2-mod-wsgi-py3 -y
pip3 install flask

mkdir -p /var/www/tictactoe/templates

# -------- Flask App --------
cat <<EOF > /var/www/tictactoe/app.py
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

board = [""] * 9
player = "X"

def check_winner():
    wins = [(0,1,2),(3,4,5),(6,7,8),
            (0,3,6),(1,4,7),(2,5,8),
            (0,4,8),(2,4,6)]
    for a,b,c in wins:
        if board[a] == board[b] == board[c] != "":
            return True
    return False

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/move", methods=["POST"])
def move():
    global player
    data = request.get_json()
    idx = data["index"]

    if board[idx] == "":
        board[idx] = player

        if check_winner():
            return jsonify({"status":"win","player":player,"board":board})

        player = "O" if player == "X" else "X"

    return jsonify({"status":"continue","board":board})

@app.route("/reset")
def reset():
    global board, player
    board = [""] * 9
    player = "X"
    return jsonify({"status":"reset"})

EOF

# -------- HTML --------
cat <<EOF > /var/www/tictactoe/templates/index.html
<!DOCTYPE html>
<html>
<head>
<title>Tic Tac Toe</title>
<style>
body { text-align:center; font-family:Arial; }
.grid { display:grid; grid-template-columns:repeat(3,100px); gap:5px; justify-content:center; }
.cell { width:100px; height:100px; font-size:30px; }
</style>
</head>
<body>

<h1>Tic Tac Toe</h1>
<div class="grid" id="board"></div>
<button onclick="resetGame()">Reset</button>

<script>
let boardDiv = document.getElementById("board");
let buttons = [];

for (let i=0;i<9;i++){
 let btn=document.createElement("button");
 btn.className="cell";

 btn.onclick=function(){
  fetch("/move",{method:"POST",headers:{"Content-Type":"application/json"},
  body:JSON.stringify({index:i})})
  .then(res=>res.json())
  .then(data=>{
    for(let j=0;j<9;j++){
      buttons[j].innerText=data.board[j];
    }
    if(data.status==="win"){
      alert("Player "+data.player+" wins!");
    }
  });
 };

 buttons.push(btn);
 boardDiv.appendChild(btn);
}

function resetGame(){
 fetch("/reset").then(()=>{
  for(let i=0;i<9;i++){buttons[i].innerText="";}
 });
}
</script>

</body>
</html>
EOF

# -------- WSGI --------
cat <<EOF > /var/www/tictactoe/tictactoe.wsgi
import sys
sys.path.insert(0, "/var/www/tictactoe")
from app import app as application
EOF

# -------- Apache Config --------
cat <<EOF > /etc/apache2/sites-available/tictactoe.conf
<VirtualHost *:80>
    WSGIScriptAlias / /var/www/tictactoe/tictactoe.wsgi

    <Directory /var/www/tictactoe>
        Require all granted
    </Directory>
</VirtualHost>
EOF

a2dissite 000-default.conf
a2ensite tictactoe
a2enmod wsgi
systemctl restart apache2
"""

# 🔹 Launch EC2
instance = ec2.run_instances(
    ImageId='ami-0f5ee92e2d63afc18',
    InstanceType='t3.micro',
    KeyName=key_name,
    SecurityGroupIds=[sg_id],
    MinCount=1,
    MaxCount=1,
    UserData=user_data
)

instance_id = instance['Instances'][0]['InstanceId']

ec2_res = boto3.resource('ec2', region_name=region)
inst = ec2_res.Instance(instance_id)

print("⏳ Waiting for instance...")
inst.wait_until_running()
inst.reload()

print("🌐 URL: http://" + inst.public_ip_address)