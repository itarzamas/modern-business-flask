from app.app import app
from flask_script import Manager
from flask_script.commands import ShowUrls


manager = Manager(app)
manager.add_command('urls',ShowUrls())
if __name__ == "__main__":
    manager.run()
