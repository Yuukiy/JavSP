import yaml
from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit
import logging
from javsp.webui.core import start_scraping
import sys
from io import StringIO

app = Flask(__name__)
socketio = SocketIO(app)

CONFIG_PATH = 'config.yml'

class SocketIOHandler(logging.Handler):
    def emit(self, record):
        socketio.emit('log', {'data': self.format(record)})

logger = logging.getLogger()
logger.addHandler(SocketIOHandler())

@app.route('/')
def index():
    return redirect(url_for('config'))

@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        config_data['scanner']['input_directory'] = request.form['scanner.input_directory']
        config_data['summarizer']['path']['output_folder_pattern'] = request.form['summarizer.path.output_folder_pattern']

        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f)

        return redirect(url_for('config'))

    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)

    return render_template('config.html', config=config_data)

@app.route('/scrape', methods=['POST'])
def scrape():
    socketio.start_background_task(start_scraping)
    return redirect(url_for('logs'))

@app.route('/logs')
def logs():
    return render_template('logs.html')

if __name__ == '__main__':
    socketio.run(app, debug=True)
