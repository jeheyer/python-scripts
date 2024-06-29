#!/usr/bin/env python3 

from flask import Flask, Response
from flask_mail import Mail, Message

app = Flask(__name__)
app.config['MAIL_SERVER']='100.77.77.77'
app.config['MAIL_PORT'] = 25
#app.config['MAIL_USERNAME'] = 'your_email@example.com'
#app.config['MAIL_PASSWORD'] = 'your_password'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)


@app.route("/")
def index():
    try:
        msg = Message('Hello from the other side!', sender = 'jeheyer@att.net', recipients = ['jeheyer@me.com'])
        msg.body = "Hey Paul, sending you this email from my Flask app, lmk if it works"
        mail.send(msg)
    except Exception as e:
        return Response(format(e), 500, content_type="text/plain")

    return "Message sent!"


if __name__ == '__main__':
    app.run()
