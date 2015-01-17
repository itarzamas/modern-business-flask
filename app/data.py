from marshmallow import Schema, fields, pprint,utils
from faker import Factory
import pickle
import os

tmt = utils.to_marshallable_type

factory = Factory()

faker = factory.create()

f = faker

def dump_fields(meta):
    for table in meta.tables.values():
        print '{}'.format(table.name)
        print '------------------------'
        print '{}'.format('\n'.join(map(str,table.c)))
        print 
        print

def dump_table(name,metadata):
    return tmt(metadata.tables[name],metadata.tables[name].columns.keys())


class PageSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    title = fields.String()
    keywords = fields.String()
    slug = fields.String()
    template_file = fields.String()
    add_right_sidebar = fields.Boolean()
    add_left_sidebar = fields.Boolean()
    add_to_nav = fields.Boolean()
    body_content = fields.String()
    date_added = fields.DateTime()
    date_modified = fields.DateTime()
    
    def __init__(self,model,*args,**kwargs):
        self._model = model
        super(PageSchema,self).__init__(*args,**kwargs)

    def make_object(self,data):
        return self._model(**data)

# coding: utf-8
def save_pages(model):
    schema = PageSchema(model,many=True)
    pages = model.query().all()
    results = schema.dump(pages)
    with open('.pages','w') as f:
        f.write(pickle.dumps(results._asdict().get('data')))

def load_page(fname):
    return pickle.loads(open(fname,'r').read())

def load_page_files():        
    return sorted(
        filter(
            lambda x: x if (
                lambda y: '.page' in y
            )(x) else None,
                    os.listdir(
                        os.path.abspath(
                            os.path.dirname(
                                os.path.dirname(
                                    __file__
                                )
                            )
                        )    
                    )
        ),
        key=lambda x: int(x.replace('.page-','')),
        #cmp=lambda x,y: int(x)-int(y)
    )

def call_method(obj,m):
    return o.__class__.__dict__[m].__call__(o) if m in o.__class__.__dict__ else None

def extract_page(filename):
    return pickle.loads(open(filename,'r').read())

def load_pages():
    return map(extract_page,load_page_files())

def load_globals():
    return pickle.loads(open('.globals','r').read())

def save_globals(g):
    with open('.globals','w') as f:
        f.write(pickle.dumps(g))


def resave_pages(model):
    schema = PageSchema(model,many=True)
    results = schema.load(pickle.loads(open('.pages','r').read()))._asdict().get('data')
    for itm in results:
    #    #for attr in dir(itm):
    #    #    if not attr.startswith('_'):
    #    #        if not callable(getattr(itm,attr)) and (type(getattr(itm,attr)) == unicode or type(getattr(itm,attr)) == str):
    #    #           setattr(itm,attr,str(getattr(itm,attr)))
        itm.save()
    #    #print type(itm)
    

def make_emails(num,user,model):
    for itm in [make_email(f.email(),model) for x in range(num)]:
        user.email_addresses.append(itm)
        itm.save()

def make_email(txt,model):
    email = model()
    email.text = txt
    email.save()
    return email

def post_data(blog_id):
    return {
        'content':f.text(),
        'title':f.word(),
        'blog_id':blog_id,
    }

def make_post(model,blog_id):
    post = model(**post_data(blog_id))
    post.save()
    return post

def make_posts(model,blogs):
    rtn = []
    for b in blogs:
        for i in range(5):
            rtn.append(make_post(model,b.id))
    return rtn
            
categorys = [
        {'name':'python','description':f.text()},
        {'name':'flask','description':f.text()},
        {'name':'another','description':f.text()},
    ]
def make_categorys(model):
    rtn = []
    for c in categorys:
        tmp = model()
        tmp.name = c['name']
        tmp.description = c['description']
        tmp.save()
        rtn.append(tmp)
    return rtn

def users():
    return {
            'username' : f.user_name(),
            'first_name' : f.first_name_male(),
            'last_name' : f.last_name(),
            'password':f.text(),
    }

def make_user(model):
    user = model(**users())
    user.save()
    return user


def make_users(user_model,email_model,blog_model):
    rtn = []
    for i in range(5):
        user = user_model(**users())
        make_emails(5,user,email_model)
        user.save()
        blogs = []
        for x in range(5):
            blogs.append(make_blog(user.id,blog_model))
        for b in blogs:
            user.blogs.append(b)
        user.save()
        rtn.append(user)
    return rtn
        
comments = {}
def make_comment(data,model):
    pass

blog = lambda aid: dict(author_id=aid,name=f.name())
            
def make_blog(aid,model):
    tmp = model()
    data = blog(aid)
    tmp.name = data['name']
    tmp.author_id = data['author_id']
    tmp.save()
    return tmp

pages = {
        'contact':'contact',
        'about':'about',
        'services':'services',
        'blog-home-1':'blog-home-1',
        'blog-home-2':'blog-home-2',
        'blog-post':'blog-post',
        'fill-width':'full-width-page',
        'fill-width-page':'full-width-page',
        'faq':'faq',
        'pricing':'pricing',
        '404':'404',
        'sidebar':'sidebar',
        'portfolio-1-col':'portfolio-1-col',
        'portfolio-2-col':'portfolio-2-col',
        'portfolio-3-col':'portfolio-3-col',
        'portfolio-4-col':'portfolio-4-col',
        'portfolio-item':'portfolio-item',
}

def make_page(slug,model):
    page = model()
    page.title = slug.title()
    page.slug = slug
    page.template_file = slug + '.html'
    if slug == 'sidebar':
        page.add_left_sidebar = True
    if 'blog' in slug:
        page.add_left_sidebar = True
    page.add_to_navbar = True
    page.save()
    return page

if __name__ == "__main__":
    from sqlalchemy.ext.automap import automap_base
    from sqlalchemy import create_engine,MetaData
    meta = MetaData()
    base = automap_base()
    e = create_engine('sqlite:///new_test.db')
    e2 = create_engine('sqlite:///newest_test.db')
    base.prepare(e,reflect=True)
    for table in  base.metadata.tables:
        base.metadata.tables[table].tometadata(meta)
    print meta.tables.keys()
    print base.classes.keys()
    print dir(base.classes['users'])
    e2.echo=True
    meta.create_all(bind=e2)


