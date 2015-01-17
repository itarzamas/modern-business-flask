from flask import url_for
from app.app import app
from flask_script import Manager
from flask_script.commands import ShowUrls

manager = Manager(app)

@manager.command
def show_urls():
    import urllib
    output = []
    for rule in app.url_map.iter_rules():
        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)
        methods = ','.join(rule.methods)
        url = rule.rule
        line = urllib.unquote("{:40s} {:40s} {}".format(url,rule.endpoint,methods))
        output.append(line)
    print '{:40s} {:40s} {}\n______________________________________________________________________________________________________________'.format('url','endpoint','methods')
    for line in sorted(output):
        print line


manager.add_command('urls',ShowUrls())
if __name__ == "__main__":
    manager.run()
