import flask
import json
from wtforms import Form,fields,meta
from filters import human_time
from LoginUtils import encrypt_password, check_password
import os
import sqlalchemy as sq
sa = sq
import datetime as dt
from data import make_page,pages,make_categorys,make_users, make_posts,resave_pages,dump_table
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.declarative.api import DeclarativeMeta
from sqlalchemy.orm import relationship, backref, sessionmaker, scoped_session
from inflection import pluralize,underscore
from flask_admin import Admin, BaseView,expose,helpers,AdminIndexView
from flask_admin.contrib.sqla.view import ModelView
from flask_macros import FlaskMacro

base = os.path.abspath(os.path.dirname(__file__))


def make_db(base,drop=False):
    if drop:
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
        uri = os.environ.get('DATABASE_URI',None) or 'sqlite:///memory/'
    e = get_engine(uri)
    sess = get_session(e)
    base = declarative_base()
    base._session = sess
    base._engine = e
    base._query = sess.query
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

    @classmethod
    def query(cls):
        if not type(cls) == DeclarativeMeta:
            return cls._query(cls)
        return cls._session.query(cls)
    
    @classmethod
    def get_by_id(cls,ident):                    
        return cls.query().get(ident)
        
    def save(self,bind=None):
        if bind is not None:
            self.metadata.bind = bind
            self._session.configure(bind=bind)
        self._session.add(self)
        self._session.commit()
        return self

    def __repr__(self):
        return '<{}: #{}-{}'.format(self.__class__.__name__,self.id,self.name)



class AuditMixin(object):
    @declared_attr
    def date_added(self):
        return sa.Column(sa.DateTime,default=dt.datetime.now)

    @declared_attr
    def date_modified(self):
        return sa.Column(sa.DateTime,onupdate=dt.datetime.now)


class MenuItem(Model):

    page = relationship("Page",backref=backref(
                        "menu_link",uselist=False))
    page_id = sa.Column(sa.Integer,sa.ForeignKey('pages.id'))
    dropdown_id = sa.Column(sa.Integer,sa.ForeignKey('menu_dropdowns.id'),nullable=True,default='null')

class MenuDropdown(Model):

    links = relationship("MenuItem",backref=backref(
                    "dropdown"),lazy="dynamic")
    icon_name = sa.Column(sa.String(255),default='')
    icon_lib = sa.Column(sa.String(255),default='glyphicon')
    
    @property
    def title(self):
        return self.name

    @property
    def icon(self):
        if self.icon_name == '':
            return self.icon_class
        return flask.Markup("<span class='{0} {0}-{1}'></span>".format(self.icon_lib,self.icon_name))


class SettingGroup(Model):

    description = sa.Column(sa.Text())
    settings = relationship('Setting',
                            lazy='dynamic',
                            backref=backref("group"),
                            cascade="all, delete-orphan",
    )

class Setting(Model):

    value = sa.Column(sa.PickleType,nullable=False)
    settings_group_id = sa.Column(sa.Integer,
                                  sa.ForeignKey(
                                    'setting_groups.id',
                                    primary_join='settings.settings_group_id==setting_group.id',
                                    ),nullable=False)

class ProductCategory(Model,AuditMixin):

    list_types = {
        '1-col':'portfolio-1-col.html',
        '2-col':'portfolio-2-col.html',
        '3-col':'portfolio-3-col.html',
        '4-col':'portfolio-4-col.html',
    }


    description = sa.Column(sa.Text)
    slug = sq.Column(sq.String(255),unique=True,nullable=False)
    list_type = sa.Column(sa.Enum('1-col','2-col','3-col','4-col'),nullable=False)
    apply_list_to_products = sa.Column(sa.Boolean(),default=True)

    def __str__(self):
        return self.name

    @property
    def list_template(self):
        return self.list_types[self.list_type]

class Product(Model,AuditMixin):

    category = relationship('ProductCategory',backref=backref(
                        'products',lazy='dynamic'))
    category_id = sa.Column(sa.Integer,sa.ForeignKey('product_categories.id'))
    description = sa.Column(sa.Text)
    slug = sq.Column(sq.String(255),unique=True,nullable=False)
    price = sa.Column(sa.String(255))
    images = relationship('ProductImage',lazy='dynamic')
    list_template = sa.Column(sa.String(255))


class ProductImage(Model,AuditMixin):
    product_id = sa.Column(sa.Integer,sa.ForeignKey('products.id'))
    filename = sa.Column(sa.String(255),nullable=False)


class Page(Model,AuditMixin):

    DEFAULT_TEMPLATE = 'page.html'

    title = sq.Column(sq.String(255),unique=True,nullable=False)
    keywords = sq.Column(sq.Text)
    slug = sq.Column(sq.String(255),unique=True,nullable=False)
    template_file = sq.Column(sq.String(255),nullable=False)
    add_right_sidebar = sq.Column(sq.Boolean,default=False)
    add_left_sidebar = sq.Column(sq.Boolean,default=False)
    add_to_nav = sq.Column(sq.Boolean,default=False)
    body_content = sq.Column(sq.Text)
    #date_added = sq.Column(sq.DateTime,default=dt.datetime.now)
    #date_modified = sq.Column(sq.DateTime,onupdate=dt.datetime.now)
    
    _current = False

    @property
    def navlink(self):
        return (self.title,self.get_absolute_url())

    def get_absolute_url(self):
        return flask.url_for('page',slug=self.slug)
    
    @classmethod
    def get_by_slug(cls,slug):
        return cls.query().filter(Page.slug==slug).first()
    
    @classmethod
    def get_page_count(cls):
        return cls.query().count()
            
    def __repr__(self):
        return '<{}: #{}-{}'.format(self.__class__.__name__,self.id,self.slug)
            
    def __str__(self):
        return unicode(self)

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
app.jinja_env.filters['human_time'] = human_time
macro = FlaskMacro(app)


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

class ProductCategoryAdmin(ModelView):
    def __init__(self,*args,**kwargs):
        ModelView.__init__(self,model=ProductCategory,session=Model._session,*args,**kwargs)

class ProductAdmin(ModelView):
    def __init__(self,*args,**kwargs):
        ModelView.__init__(self,model=Product,session=Model._session,*args,**kwargs)

class ProductImageAdmin(ModelView):
    def __init__(self,*args,**kwargs):
        ModelView.__init__(self,model=ProductImage,session=Model._session,*args,**kwargs)



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
                form=''
        )
class IndexView(AdminIndexView):
    @expose()
    def dex(self,*args,**kwargs):
        return self.render('admin/dashboard.html')

admin = Admin(app=app,name='Site Admin',index_view=IndexView(),template_mode='bootstrap3')

@app.route('/test')
def test():
    return flask.render_template('test.html')

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
    cats = Category.query().all()
    if id_num is not None:
        post = Post._session.query(Post).get(id_num)
    else:
        post = None
    return flask.render_template('blog-post.html',add_rightbar=True,post=post,form=form,cats=cats)

for c,a in [
        ('settings',ContactUsAdmin),
        ('cms',PageAdmin),
        ('cms',BlogAdmin),
        ('cms',PostAdmin),
        ('cms',CategoryAdmin),
        ('settings',UserAdmin),
        ('cms',CommentAdmin),
        ('settings',SettingsAdmin),
        ('shop',ProductAdmin),
        ('shop',ProductImageAdmin),
        ('shop',ProductCategoryAdmin),
        ]:
    admin.add_view(a(category=c))

@app.route('/<slug>')
def page(slug):
    class TestForm(Form):
        test = fields.RadioField('test',choices=(
                                            ('val','label'),
                                            ('val2','label2'),
                                            ('val3','label3'),
                                            ('val4','label4'),
                                        )
                                )
    test = TestForm()
    file_name = None
    content = ''
    page_name = ''
    if '.html' in slug:
        file_name = slug
        slug = slug.split('.html')[0]
    page = Page._session.query(Page).filter(Page.slug==slug).all()
    if len(page) != 0:
        if page is not None:
            page = page[0]
            content = page.body_content
            template_file = page.template_file if os.path.exists(page.template_file) else page.DEFAULT_TEMPLATE
            page_name = page.name
            title = page.title
    elif file_name is not None:
        template_file = file_name
        title = slug
    else:
        template_file = slug + '.html'
        title = slug
    return flask.render_template(template_file,content=content,page_title=title,page_name=page_name,test=test)


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
    app.jinja_env.globals['page_width'] = '-fluid'
    app.jinja_env.globals['pages'] = pages
    app.jinja_env.globals['slug'] = slug

@app.before_request
def get_contact_us_data():
    data = json.loads(open(os.path.join(base,'contact_data.json'),'r').read())
    app.jinja_env.globals['data'] = data

class KillerMiddleware(object):
    def __init__(self,app):
        self._app = app
        
    def __call__(self,e,s):
        return self._app(e,s)

app.wsgi_app = KillerMiddleware(app.wsgi_app)

if __name__ == "__main__":
    if os.environ.get('DATABASE_URI'):
        if os.environ.get('CREATE_DATABASE',False):
            make_db(Model)
            resave_pages(Page)
            make_categorys(Category)
            make_users(User,EmailAddress,Blog)
            blogs = Blog._session.query(Blog).all()
            make_posts(Post,blogs)
    import sys
    #print dump_table(sys.argv[1],Model.metadata)
    #sys.exit()
    port = '8080'
    if os.environ.get('PORT',False):
        port = os.environ.get('PORT')
    app.run(host='0.0.0.0',port=port,debug=True)
