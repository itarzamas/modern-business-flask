import flask
import json
from wtforms import Form,fields,meta
from LoginUtils import encrypt_password, check_password
import os
import sqlalchemy as sq
sa = sq
import datetime as dt
from data import make_page,pages,make_categorys,make_users, make_posts
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship, backref, sessionmaker, scoped_session
from inflection import pluralize,underscore
from flask_admin import Admin, BaseView,expose,helpers
from flask_admin.contrib.sqla.view import ModelView

base = os.path.abspath(os.path.dirname(__file__))


def make_db(base):
    base.metadata.drop_all(bind=base._engine)
    base.metadata.create_all(bind=base._engine)

def get_engine(uri):
    e = sq.create_engine(uri)
    e.echo = True
    return e

def get_session(e):
    return scoped_session(
            sessionmaker(bind=e)
    )

def get_db(uri=None):
    if uri is None:
        if 'DATABASE_URI' not in os.environ:
            raise Exception
        uri = os.environ.get('DATABASE_URI')
    e = get_engine(uri)
    sess = get_session(e)
    base = declarative_base()
    base._session = sess
    base._engine = e
    return base

_Model = get_db()

class Model(_Model):
    __abstract__ = True

    @staticmethod
    def make_table_name(name):
        return pluralize(underscore(name))

    @declared_attr
    def __tablename__(self):
        return Model.make_table_name(self.__name__)

    @declared_attr
    def id(self):
        return sq.Column(sq.Integer,primary_key=True)

    @declared_attr
    def name(self):
        return sq.Column(sq.String(255))
    
    @classmethod
    def create(cls,**kwargs):
        instance = cls(**kwargs)
        instance.save()
        return instance

    def query(self):
        return self._session.query(self)
    
    def save(self):
        self._session.add(self)
        self._session.commit()
        return self


class Page(Model):

    title = sq.Column(sq.String(255),unique=True,nullable=False)
    keywords = sq.Column(sq.Text)
    slug = sq.Column(sq.String(255),unique=True,nullable=False)
    template_file = sq.Column(sq.String(255),nullable=False)
    add_right_sidebar = sq.Column(sq.Boolean,default=False)
    add_left_sidebar = sq.Column(sq.Boolean,default=False)
    add_to_nav = sq.Column(sq.Boolean,default=False)
    body_content = sq.Column(sq.Text)
    date_added = sq.Column(sq.DateTime,default=dt.datetime.now)
    date_modified = sq.Column(sq.DateTime,onupdate=dt.datetime.now)
    
    _current = False

    @property
    def navlink(self):
        return (self.title,self.get_absolute_url())


    def get_absolute_url(self):
        return flask.url_for('page',slug=self.slug)

    def __unicode__(self):
        return self.title

class Blog(Model):
    
    start_date = sa.Column(sa.DateTime,default=dt.datetime.now)
    author = relationship('User',backref=backref(
                'blogs',lazy='dynamic'))
    author_id = sq.Column(sa.Integer,sa.ForeignKey('users.id'))
    category = relationship('Category')
    category_id = sa.Column(sa.Integer,sa.ForeignKey('categories.id'))
    posts = relationship('Post',lazy='dynamic',backref=backref('blog'))

    def get_absolute_url(self):
        return flask.url_for('blog_post_list',id_num=self.id)

    @property
    def title(self):
        return self.name


    @property
    def post_list_url(self):
        return self.get_absolute_url()


#class BlogData(Model):

#    icon = sa.Column(sa.String(255))
#    description = sa.Column(sa.Text)
#    blog_id = sa.Column(sa.Integer,sa.ForeignKey('blogs.id'))
#    blog = relationship('Blog',backref=backref(
#                'data',uselist=False))



class Category(Model):
    
    description = sa.Column(sa.Text)

    def __unicode__(self):
        return self.name


class EmailForm(Form):
    text = fields.StringField('address',validators=[])
    user_id = fields.HiddenField('user_id')


class EmailAddress(Model):
    
    text = sa.Column(sa.String(255),unique=True,nullable=False)
    user_id = sa.Column(sa.Integer,sa.ForeignKey('users.id'))
    user = relationship('User',backref=backref(
                'email_addresses',lazy='dynamic'))

    def __unicode__(self):
        return self.text


class Post(Model):
    
    blog_id = sa.Column(sa.Integer,sa.ForeignKey('blogs.id'))
    content = sa.Column(sa.Text)
    title = sa.Column(sa.String(255),default='')
    keywords = sa.Column(sa.Text)
    date_added = sa.Column(sa.DateTime,default=dt.datetime.now)
    date_modified = sa.Column(sa.DateTime,onupdate=dt.datetime.now)
    comments = relationship('Comment')


    def __unicode__(self):
        return '{}: from {}'.format(self.title,self.blog.name)

    def get_absolute_url(self):
        return flask.url_for('blog_post',id_num=self.id)

class Comment(Model):

    post_id = sa.Column(sa.Integer,sa.ForeignKey('posts.id'))
    user_id = sa.Column(sa.Integer,sa.ForeignKey('users.id'))
    email_id = sa.Column(sa.Integer,sa.ForeignKey('email_addresses.id'))
    content = sa.Column(sa.Text)
    approved = sa.Column(sa.Boolean,default=False)
    denied = sa.Column(sa.Boolean,default=False)
    date_added = sa.Column(sa.DateTime,default=dt.datetime.now)

class User(Model):
    
    username = sa.Column(sa.String(255),nullable=False,unique=True)
    first_name = sa.Column(sa.String(255))
    last_name = sa.Column(sa.String(255))
    _password = sa.Column(sa.Text,nullable=False)

    def __unicode__(self):
        return self.username

    @property
    def password(self):
        return None

    @password.setter
    def password(self,pw):
        hsh = encrypt_password(pw)
        self._password = hsh

app = flask.Flask(__name__)
app.config['SECRET_KEY'] = 'fvervrvwe'
admin = Admin(app,template_mode='bootstrap3')

class PageAdmin(ModelView):
    column_list = ['title','slug','template_file','date_modified']

    def __init__(self,*args,**kwargs):
        ModelView.__init__(self,model=Page,session=Model._session,*args,**kwargs)

class ContactUsSettingsForm(Form):
    address = fields.StringField('Business Address')
    email = fields.StringField('Contact Email')
    phone = fields.StringField('Contact Phone Number')
    hours = fields.StringField('Company Hours')
    facebook_link = fields.StringField('Facebook link')
    twitter_link = fields.StringField('twitter Link')
    google_link = fields.StringField('Google+ link')


class ContactUsAdmin(BaseView):
    @expose('/',methods=['post','get'])
    def index(self):

        form = ContactUsSettingsForm(flask.request.form)
        if flask.request.method.lower() == 'post':
            data = dict(
                address=form.address.data,
                email=form.email.data,
                phone=form.phone.data,
                hours=form.hours.data,
                facebook_link=form.facebook_link.data,
                twitter_link=form.twitter_link.data,
                google_link=form.google_link.data,
            )
            with open(os.path.join(base,'contact_data.json'),'w') as f:
                f.write(json.dumps(data))
        data = json.loads(open(os.path.join(base,'contact_data.json'),'r').read())
        form = ContactUsSettingsForm(**data)
        return self.render('admin/settings.html',form=form)



class BlogAdmin(ModelView):
    def __init__(self,*args,**kwargs):
        ModelView.__init__(self,model=Blog,session=Model._session,*args,**kwargs)

class PostAdmin(ModelView):
    def __init__(self,*args,**kwargs):
        ModelView.__init__(self,model=Post,session=Model._session,*args,**kwargs)

class UserAdmin(ModelView):
    column_list = ['username','first_name']
    #inline_models = (EmailAddress,)
    
    
    def get_form(obj=None):
        form = super(UserAdmin,obj).get_form()
        form._meta = meta
        return form



    def __init__(self,*args,**kwargs):
        ModelView.__init__(self,model=User,session=Model._session,*args,**kwargs)

class CategoryAdmin(ModelView):
    def __init__(self,*args,**kwargs):
        ModelView.__init__(self,model=Category,session=Model._session,*args,**kwargs)

class CommentAdmin(ModelView):
    def __init__(self,*args,**kwargs):
        ModelView.__init__(self,model=Comment,session=Model._session,*args,**kwargs)

class CommentForm(Form):
    email = fields.StringField('Your Email')
    comment = fields.TextAreaField('Your Comment')
    submit = fields.SubmitField('submit')


class SettingsAdmin(BaseView):
    base_template = 'admin/base.html'
    @expose()
    def index(self,*args,**kwargs):
        return flask.render_template(
                'admin/settings.html',
                admin_base_template=self.base_template,
                admin_view=self,
                h=helpers,
        )

@app.route('/')
def index():
    return flask.render_template('index.html')

@app.route('/contact',methods=['post','get'])
@app.route('/contact.html',methods=['post','get'])
def contact():
    return flask.render_template('contact.html',base=base)

@app.route('/sidebar',methods=['post','get'])
@app.route('/sidebar.html',methods=['post','get'])
def sidebar():
    return flask.render_template('sidebar.html',add_leftbar=True)

@app.route('/portfolio-item')
@app.route('/portfolio-item/<int:item_num>')
@app.route('/portfolio-item.html')
def portfolio_item(item_num=None):
    if item_num is None:
        item_num = 1
    return flask.render_template('portfolio-item.html',item=item_num)

@app.route('/blog-home/<int:num>')
@app.route('/blog-home.html/<int:num>')
def blog_home(num=None):
    if num in [1,2] or num is None:
        if num is None:
            template = flask.request.path
        else:
            template = 'blog-home-{}.html'.format(num)
        blogs = Blog._session.query(Blog).all()
        return flask.render_template(template,add_rightbar=True,blogs=blogs)
    else:
        return flask.abort(404)


@app.route('/blog/<int:id_num>')
def blog_post_list(id_num):
    blog = Blog._session.query(Blog).get(id_num)
    posts = blog.posts or ['']
    return flask.render_template('blog-home-1.html',blog=blog,posts=posts,add_rightbar=True,content_width=9)


@app.route('/blog-post/<int:id_num>')
@app.route('/blog-post')
@app.route('/blog-post.html')
def blog_post(id_num=None):
    form = CommentForm()
    if id_num is not None:
        post = Post._session.query(Post).get(id_num)
    else:
        post = None
    return flask.render_template('blog-post.html',add_rightbar=True,post=post,form=form)

for a in [ContactUsAdmin,PageAdmin,BlogAdmin,PostAdmin,CategoryAdmin,UserAdmin,CommentAdmin,SettingsAdmin]:
    admin.add_view(a())

@app.route('/<slug>')
def page(slug):
    if '.html' in slug:
        slug = slug.split('.html')[0]
    page = Page._session.query(Page).filter(Page.slug==slug).all()[0]
    if not page is None:
        content = page.body_content
    return flask.render_template(page.template_file,content=content,page_title=page.title)


@app.before_request
def add_pages():
    pages = Page._session.query(Page).filter(Page.add_to_nav==True).all()
    if flask.request.view_args:
        slug = flask.request.view_args.get('slug')
    else:
        slug = None
    if slug is None:
        slug = flask.request.endpoint
    for page in pages:
        if page.slug == slug:
            page._current = True
        else:
            page._current = False
    app.jinja_env.globals['pages'] = pages
    app.jinja_env.globals['slug'] = {'slug':slug}



@app.before_request
def get_contact_us_data():
    data = json.loads(open(os.path.join(base,'contact_data.json'),'r').read())
    app.jinja_env.globals['data'] = data



if __name__ == "__main__":
    if os.environ.get('DATABASE_URI'):
        if os.environ.get('CREATE_DATABASE',False):
            make_db(Model)
            for page in pages:
                make_page(page,Page)
            make_categorys(Category)
            make_users(User,EmailAddress,Blog)
            blogs = Blog._session.query(Blog).all()
            make_posts(Post,blogs)
    app.run(host='0.0.0.0',port=8080,debug=True)

