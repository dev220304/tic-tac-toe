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
            return jsonify({
                "status": "win",
                "player": player,
                "board": board
            })

        player = "O" if player == "X" else "X"

    return jsonify({
        "status": "continue",
        "board": board
    })

@app.route("/reset")
def reset():
    global board, player
    board = [""] * 9
    player = "X"
    return jsonify({"status": "reset"})

if __name__ == "__main__":
    app.run(debug=True)