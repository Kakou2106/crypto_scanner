from flask import Flask, render_template
import pandas as pd
import numpy as np

app = Flask(__name__)

@app.route('/')
def dashboard():
    # Ton code de dashboard ici
    return render_template('dashboard.html')

if __name__ == '__main__':
    app.run(debug=True)