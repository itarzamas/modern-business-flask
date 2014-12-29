from faker import Factory

factory = Factory()

faker = factory.create()

f = faker

def make_emails(num,model):
    return [make_email(f.email(),model) for x in range(num)]

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
        emails = make_emails(5,email_model)
        user = user_model(**users())
        user.emails = emails
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


