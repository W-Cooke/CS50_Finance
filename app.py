import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

# function to take string input from database (formatted as "$0,000.00" and return a simple float e.g: "0000.00")
def backToFloat(string):
    try:
        float(string)
        return float(string)
    except ValueError:
        string = string.strip("$")
        string = string.replace(",", "")
        return float(string)

# function to receive cash information from current user in form of a float
def getCurrentUserCash():
    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

    # extracting cash value from the dict inside the list
    if isinstance(cash, list):
        if cash:
            cash = cash.pop()
            cash = cash["cash"]
        else:
            return None

    # using function declared above to change cash value to a float for easy calculations
    if isinstance(cash, str):
        cash = backToFloat(cash)
    return cash

# function for checking for valid number of shares (whole numbers only, no other characters)
def numCheck(string):
    if string.isdigit():
        if int(string) > 0:
            return int(string)
    else:
        return None


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # get current user information
    cash = total = getCurrentUserCash()
    userStocks = db.execute("SELECT * FROM stocks WHERE user_id = ?", session["user_id"])

    # check db request returned valid
    if not userStocks:
        return apology("database error", 200)

    #iterate through stock information, updating with lookup for consistent information
    for item in userStocks:
        stockInfo = lookup(item["symbol"])
        item["name"] = stockInfo["name"]
        item["price"] = stockInfo["price"]
        item["total"] = item["price"] * item["holding"]

        # calculate totals
        total += item["total"]

        # change values to dollar values
        item["price"] = usd(item["price"])
        item["total"] = usd(item["total"])
    cash = usd(cash)
    total = usd(total)

    # return data to render template
    return render_template("index.html", userStocks=userStocks, cash=cash, total=total)



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        # check amount is valid
        amount = numCheck(request.form.get("shares"))
        if amount == None:
            return apology("invalid share amount")

        # check symbol is valid
        symbol = lookup(request.form.get("symbol"))
        if symbol == None:
            return apology("Stock symbol doesn't exist")

        # calculate cost of shares * amount to be bought
        cost = symbol["price"] * amount

        # make sure user has enough cash
        cash = getCurrentUserCash()
        if(cash < cost):
            return apology("Not enough funds")

        # remove amount from users cash reserves
        cash -= cost
        cash = usd(cash)
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"])

        # add stock and amount and price
        db.execute("INSERT INTO stocks (user_id, name, symbol, holding, price_at_purchase) VALUES (?, ?, ?, ?, ?)", session["user_id"], symbol["name"], symbol["symbol"], amount, symbol["price"])

        # log transaction
        db.execute("INSERT INTO transaction_history (user_id, name, symbol, transaction_type, amount, price_at_purchase) VALUES (?, ?, ?, ?, ?, ?)", session["user_id"], symbol["name"], symbol["symbol"], "buy", amount, symbol["price"])
        #return to index page
        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transHistory = db.execute("SELECT * FROM transaction_history WHERE user_id = ? ORDER BY time_stamp DESC", session["user_id"])
    if not transHistory:
        return apology("Database Error")
    return render_template("/history.html", transHistory=transHistory)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        # Take stock symbol from page and run it through lookup function
        stockSymbol = lookup(request.form.get("symbol"))

        # redirect to webpage if lookup is valid
        if stockSymbol:
            return render_template("/quoted.html", stockSymbol=stockSymbol)

        # else return apology page
        else:
            return apology("Stock symbol doesn't exist")
    else:
        return render_template("/quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        nonAlphaNum = ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+", "-", "=", "[", "]", "{", "}", ";", ":", '"', ",", ".", "/", "<", ">", "?", "`", "~", "|"]
        SQL_protections = [";", ")", "'"]

        # check if username was submitted
        if not username:
            return apology("Username Required")

        # check to protect against malicious SQL code in username
        if any(char in SQL_protections for char in username):
            return apology("Cannot use ';', ')' or ''; in username")

        # check if password was submitted
        if not password or not confirmation:
            return apology("Password Required")

        # check that passwords match
        if password != confirmation:
            return apology("Passwords do not match")

        # check password length is valid
        if len(password) < 8:
            return apology("password must be at least 8 characters long")

        # password has at least one special character
        if not any(char in nonAlphaNum for char in password):
            return apology("password must contain one non-alphanumeric character")

        # password has at least one uppercase character
        if not any(char.isupper() for char in password):
            return apology("password must contain at least one uppercase character")

        # password has at one number
        if not any(char.isdigit() for char in password):
            return apology("password must contain at least one number")

        #check to see if username exists in database
        nameCheck = db.execute("SELECT username FROM users WHERE username = ?", username)
        if nameCheck:
            return apology("Username already exists, please pick another one")

        # hash password
        pWordHash = generate_password_hash(password)

        # add user to database
        db.execute("INSERT INTO users (username, hash) VALUES ( ?, ?)", username, pWordHash)

        # login user and remember session
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        session["user_id"] = rows[0]["id"]

        # redirect to homepage
        return redirect("/", 200)
    else:
        return render_template("/register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":

        amount = numCheck(request.form.get("shares"))
        symbol = request.form.get("symbol")

        # check amount is valid
        if amount == None:
            return apology("Invalid share amount")

        #check stock is valid
        stockSymbol = lookup(symbol)
        if stockSymbol == None:
            return apology("stock symbol is invalid")
        else:
            # change symbol to data from lookup, this handles changing the symbol to uppercase
            symbol = stockSymbol["symbol"]

        # check user has enough shares to sell
        sharesOwned = db.execute("SELECT * FROM stocks WHERE user_id = ? AND symbol = ?", session["user_id"], symbol)
        if not sharesOwned:
            return apology("user doesn't own shares in this stock")

        # access list to return dict
        if isinstance(sharesOwned, list):
            sharesOwned = sharesOwned.pop()

        # check amount of stocks to sell against amount owned
        if sharesOwned["holding"] < amount:
            return apology("invalid share amount")

        # if user is selling all their stocks
        elif sharesOwned["holding"] == amount:

            # calculate value of shares
            price = stockSymbol["price"] * amount

            # log sell transaction
            db.execute("INSERT INTO transaction_history (user_id, name, symbol, transaction_type, amount, price_at_purchase) VALUES (?, ?, ?, ?, ?, ?)", session["user_id"], stockSymbol["name"], stockSymbol["symbol"], "sell", amount, stockSymbol["price"])

            # update user's cash
            cash = getCurrentUserCash()
            cash += price
            cash = usd(cash)
            db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"])

            # delete entry from stocks
            db.execute("DELETE FROM stocks WHERE id = ?", sharesOwned["id"])

        #if user is selling partial amount
        elif sharesOwned["holding"] > amount:

            newAmount = sharesOwned["holding"] - amount
            # calculate value of shares

            price = stockSymbol["price"] * amount

            # log sell transaction
            db.execute("INSERT INTO transaction_history (user_id, name, symbol, transaction_type, amount, price_at_purchase) VALUES (?, ?, ?, ?, ?, ?)", session["user_id"], stockSymbol["name"], stockSymbol["symbol"], "sell", amount, stockSymbol["price"])

            # update user's cash
            cash = getCurrentUserCash()
            cash += price
            cash = usd(cash)
            db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"])

            # update entry from stocks
            db.execute("UPDATE stocks SET holding = ? WHERE id = ?", newAmount, sharesOwned["id"])

        return redirect("/")
    else:

        # send information of stock symbols owned for user to select from on sell page
        symbols = db.execute("SELECT symbol FROM stocks WHERE user_id = ?", session["user_id"])
        return render_template("sell.html", symbols=symbols)


@app.route("/bailout", methods=["GET", "POST"])
@login_required
def bailout():
    """Get stock quote."""
    if request.method == "POST":
        # Very unserious page that allows a user a free $10,000 if their cash reserves are running low

        # get user's current cash total
        userCash = getCurrentUserCash()
        if userCash == None:
            return apology("Database error")

        # if their cash is below $1,000, add $10,000 to their account
        if userCash < 1000.00:
            userCash += 10000.00
            userCash = usd(userCash)
            db.execute("UPDATE users SET cash = ? WHERE id = ?", userCash, session["user_id"])
            return render_template("index.html")
        else:
            return apology("Naughty naughty! you have plenty of cash")
    else:
        return render_template("/bailout.html")