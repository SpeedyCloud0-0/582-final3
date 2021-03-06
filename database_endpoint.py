from flask import Flask, request, g
from flask_restful import Resource, Api
from sqlalchemy import create_engine, select, MetaData, Table
from flask import jsonify
import json
import eth_account
import algosdk
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import load_only

from models import Base, Order, Log

engine = create_engine('sqlite:///orders.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)

app = Flask(__name__)


# These decorators allow you to use g.session to access the database inside the request code
@app.before_request
def create_session():
    g.session = scoped_session(
        DBSession)  # g is an "application global" https://flask.palletsprojects.com/en/1.1.x/api/#application-globals


@app.teardown_appcontext
def shutdown_session(response_or_exc):
    g.session.commit()
    g.session.remove()


"""
-------- Helper methods (feel free to add your own!) -------
"""


def log_message(d):
    # Takes input dictionary d and writes it to the Log table
    pass


"""
---------------- Endpoints ----------------
"""


@app.route('/trade', methods=['POST'])
def trade():
    if request.method == "POST":
        content = request.get_json(silent=True)
        print(f"content = {json.dumps(content)}")
        columns = ["sender_pk", "receiver_pk", "buy_currency", "sell_currency", "buy_amount", "sell_amount", "platform"]
        fields = ["sig", "payload"]
        error = False
        for field in fields:
            if not field in content.keys():
                print(f"{field} not received by Trade")
                print(json.dumps(content))
                log_message(content)
                return jsonify(False)

        error = False
        for column in columns:
            if not column in content['payload'].keys():
                print(f"{column} not received by Trade")
                error = True
        if error:
            print(json.dumps(content))
            log_message(content)
            return jsonify(False)

        # Your code here
        # Note that you can access the database session using g.session

        # Check what platform it is
        signature = content.get("sig")
        message = json.dumps(content.get("payload"))
        pk = content.get("payload").get("sender_pk")
        platform = content.get("payload").get("platform")
        if platform == 'Ethereum':
            # Check if signature is valid
            encoded_msg = eth_account.messages.encode_defunct(text=message)
            result = (eth_account.Account.recover_message(encoded_msg, signature=signature) == pk)
        else:
            # Check if signature is valid
            result = algosdk.util.verify_bytes(message.encode('utf-8'), signature, pk)

        if result:
            order = content['payload']
            order_obj = Order(sender_pk=order['sender_pk'], receiver_pk=order['receiver_pk'],
                              buy_currency=order['buy_currency'], sell_currency=order['sell_currency'],
                              buy_amount=order['buy_amount'], sell_amount=order['sell_amount'],
                              signature=content['sig'])
            g.session.add(order_obj)
            g.session.commit()
            return jsonify(True)
        else:
            log_message(content['payload'])
            return jsonify(False)


@app.route('/order_book')
def order_book():
    # Your code here
    # Note that you can access the database session using g.session
    orders = [order for order in g.session.query(Order).all()]
    data = []
    for existing_oder in orders:
        json_order = {'sender_pk': existing_oder.sender_pk, 'receiver_pk': existing_oder.receiver_pk,
                      'buy_currency': existing_oder.buy_currency, 'sell_currency': existing_oder.sell_currency,
                      'buy_amount': existing_oder.buy_amount, 'sell_amount': existing_oder.sell_amount,
                      'signature': existing_oder.signature}

        data.append(json_order)
    result = {"data": data}
    return jsonify(result)


if __name__ == '__main__':
    app.run(port='5002')
