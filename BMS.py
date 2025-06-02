import mysql.connector
import getpass
from datetime import datetime

class BankManagement:
    def __init__(self):
        self.db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="bankdb",
            auth_plugin="mysql_native_password"
        )
        self.cursor = self.db.cursor()
        self.admin_user = "admin"
        self.admin_pass = "admin123"
        self.current_user = None
        self.create_tables()

    def create_tables(self):
        # Accounts table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(100) UNIQUE,
            password VARCHAR(100),
            balance DECIMAL(15,2) DEFAULT 0.00
        )""")
        # Transactions table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            account_id INT,
            type VARCHAR(50),
            amount DECIMAL(15,2),
            date DATETIME,
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )""")
        self.db.commit()

    def register(self):
        name = input("Name: ")
        email = input("Email: ")
        if "@" not in email:
            print("Invalid email")
            return
        self.cursor.execute("SELECT * FROM accounts WHERE email=%s", (email,))
        if self.cursor.fetchone():
            print("Email already registered")
            return
        password = getpass.getpass("Create password: ")
        # Initial deposit optional, start at 0
        self.cursor.execute(
            "INSERT INTO accounts (name, email, password) VALUES (%s, %s, %s)",
            (name, email, password)
        )
        self.db.commit()
        print("Registration successful. Your initial balance is 0.00")

    def login(self):
        email = input("Email: ")
        password = getpass.getpass("Password: ")
        # Check for admin
        if email == self.admin_user and password == self.admin_pass:
            print("Welcome, Admin")
            self.admin_menu()
            return
        # Check for normal user
        self.cursor.execute(
            "SELECT id, name FROM accounts WHERE email=%s AND password=%s",
            (email, password)
        )
        result = self.cursor.fetchone()
        if result:
            self.current_user = {
                'id': result[0],
                'name': result[1]
            }
            print(f"Welcome, {result[1]}")
            self.user_menu()
        else:
            print("Invalid credentials")

    def admin_menu(self):
        while True:
            print("\n1.View All Accounts\n2.View All Transactions\n3.Logout")
            choice = input("Choice: ")
            if choice == "1":
                self.view_accounts()
            elif choice == "2":
                self.view_transactions()
            elif choice == "3":
                break
            else:
                print("Invalid choice")

    def user_menu(self):
        while True:
            print("\n1.View Balance\n2.Deposit\n3.Withdraw\n4.Transfer\n5.Transaction History\n6.Logout")
            choice = input("Choice: ")
            if choice == "1":
                self.view_balance()
            elif choice == "2":
                self.deposit()
            elif choice == "3":
                self.withdraw()
            elif choice == "4":
                self.transfer()
            elif choice == "5":
                self.transaction_history()
            elif choice == "6":
                self.current_user = None
                break
            else:
                print("Invalid choice")

    def view_accounts(self):
        self.cursor.execute("SELECT id, name, email, balance FROM accounts")
        accounts = self.cursor.fetchall()
        if not accounts:
            print("No accounts found")
            return
        print("ID | Name | Email | Balance")
        for acc in accounts:
            print(f"{acc[0]} | {acc[1]} | {acc[2]} | {acc[3]}")

    def view_transactions(self):
        self.cursor.execute(
            "SELECT t.id, a.name, t.type, t.amount, t.date FROM transactions t "
            "JOIN accounts a ON t.account_id = a.id"
        )
        txns = self.cursor.fetchall()
        if not txns:
            print("No transactions found")
            return
        print("TxnID | Account | Type | Amount | Date")
        for txn in txns:
            print(f"{txn[0]} | {txn[1]} | {txn[2]} | {txn[3]} | {txn[4]}")

    def view_balance(self):
        self.cursor.execute("SELECT balance FROM accounts WHERE id=%s", (self.current_user['id'],))
        balance = self.cursor.fetchone()[0]
        print(f"Your current balance is: {balance:.2f}")

    def deposit(self):
        amount = input("Enter amount to deposit: ")
        try:
            amt = float(amount)
            if amt <= 0:
                print("Amount must be positive")
                return
        except ValueError:
            print("Invalid amount")
            return
        # Update balance
        self.cursor.execute(
            "UPDATE accounts SET balance = balance + %s WHERE id=%s", (amt, self.current_user['id'])
        )
        # Record transaction
        self.cursor.execute(
            "INSERT INTO transactions (account_id, type, amount, date) VALUES (%s, %s, %s, %s)",
            (self.current_user['id'], 'Deposit', amt, datetime.now())
        )
        self.db.commit()
        print(f"Deposited {amt:.2f} successfully")

    def withdraw(self):
        amount = input("Enter amount to withdraw: ")
        try:
            amt = float(amount)
            if amt <= 0:
                print("Amount must be positive")
                return
        except ValueError:
            print("Invalid amount")
            return
        # Check balance
        self.cursor.execute("SELECT balance FROM accounts WHERE id=%s", (self.current_user['id'],))
        balance = float(self.cursor.fetchone()[0])
        if amt > balance:
            print("Insufficient funds")
            return
        # Update balance
        self.cursor.execute(
            "UPDATE accounts SET balance = balance - %s WHERE id=%s", (amt, self.current_user['id'])
        )
        # Record transaction
        self.cursor.execute(
            "INSERT INTO transactions (account_id, type, amount, date) VALUES (%s, %s, %s, %s)",
            (self.current_user['id'], 'Withdrawal', amt, datetime.now())
        )
        self.db.commit()
        print(f"Withdrew {amt:.2f} successfully")

    def transfer(self):
        target_email = input("Enter recipient's email: ")
        amount = input("Enter amount to transfer: ")
        try:
            amt = float(amount)
            if amt <= 0:
                print("Amount must be positive")
                return
        except ValueError:
            print("Invalid amount")
            return
        # Fetch sender balance
        self.cursor.execute("SELECT balance FROM accounts WHERE id=%s", (self.current_user['id'],))
        balance = float(self.cursor.fetchone()[0])
        if amt > balance:
            print("Insufficient funds")
            return
        # Fetch recipient
        self.cursor.execute("SELECT id FROM accounts WHERE email=%s", (target_email,))
        result = self.cursor.fetchone()
        if not result:
            print("Recipient not found")
            return
        recipient_id = result[0]
        # Perform transfer
        self.cursor.execute(
            "UPDATE accounts SET balance = balance - %s WHERE id=%s", (amt, self.current_user['id'])
        )
        self.cursor.execute(
            "UPDATE accounts SET balance = balance + %s WHERE id=%s", (amt, recipient_id)
        )
        # Record transactions
        self.cursor.execute(
            "INSERT INTO transactions (account_id, type, amount, date) VALUES (%s, %s, %s, %s)",
            (self.current_user['id'], f'Transfer to {target_email}', amt, datetime.now())
        )
        self.cursor.execute(
            "INSERT INTO transactions (account_id, type, amount, date) VALUES (%s, %s, %s, %s)",
            (recipient_id, f'Transfer from {self.current_user["id"]}', amt, datetime.now())
        )
        self.db.commit()
        print(f"Transferred {amt:.2f} to {target_email} successfully")

    def transaction_history(self):
        self.cursor.execute(
            "SELECT type, amount, date FROM transactions WHERE account_id=%s ORDER BY date DESC", (self.current_user['id'],)
        )
        txns = self.cursor.fetchall()
        if not txns:
            print("No transactions found")
            return
        print("Type | Amount | Date")
        for txn in txns:
            print(f"{txn[0]} | {txn[1]:.2f} | {txn[2]}")

    def home(self):
        while True:
            print("\n1.Register\n2.Login\n3.Exit")
            choice = input("Choice: ")
            if choice == "1":
                self.register()
            elif choice == "2":
                self.login()
            elif choice == "3":
                break
            else:
                print("Invalid choice")

if __name__ == '__main__':
    app = BankManagement()
    app.home()