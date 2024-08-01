from flask import Flask, redirect, request, render_template, url_for#, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, and_
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
#from sqlalchemy.exc import IntegrityError
from datetime import date
from os import urandom
import mimetypes 
mimetypes.add_type("text/css",".css",True)

# Instantiate App
app = Flask(__name__)
app.secret_key=urandom(24)

bcrypt=Bcrypt(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///libraryManagementDatabase.sqlite3'
db = SQLAlchemy()
db.init_app(app)
app.app_context().push()

login_manager=LoginManager()
login_manager.login_view='auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(erpid):
    return User.query.get(int(erpid))

class Books(db.Model):
    __tablename__='books'
    isbn = db.Column(db.Integer, primary_key=True)
    book_name=db.Column(db.String,nullable=False)
    author=db.Column(db.String,nullable=False)
    publication=db.Column(db.String,nullable=False)
    total_copies=db.Column(db.Integer,nullable=False)
    available_copies=db.Column(db.Integer,nullable=False)

class User(UserMixin,db.Model):
    __tablename__='user'
    erp = db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String,nullable=False)
    password=db.Column(db.String,nullable=False)
    role=db.Column(db.String,nullable=False)   

    def get_id(self):
        return (self.erp)

class Issued(db.Model):
    __tablename__='issued_books'
    issueId = db.Column(db.Integer, autoincrement=True, primary_key=True)
    isbnissue = db.Column(db.Integer, db.ForeignKey('books.isbn'), nullable=False)
    erpissue = db.Column(db.Integer, db.ForeignKey('user.erp'), nullable=False)
    date=db.Column(db.String,nullable=False)
    status=db.Column(db.String,nullable=False)  

class History(db.Model):
    __tablename__='history'
    issueId = db.Column(db.Integer ,primary_key=True)
    isbnissue = db.Column(db.Integer, db.ForeignKey('books.isbn'), nullable=False)
    erpissue = db.Column(db.Integer, db.ForeignKey('user.erp'), nullable=False)
    date=db.Column(db.String,nullable=False)
    status=db.Column(db.String,nullable=False) 

#Common Functions

@app.route('/',methods=['GET'])
def home():
    books=db.session.query(Books).order_by(Books.book_name.asc()).all()
    return render_template("common/home.html",books=books)

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='GET':
        return render_template('common/login.html')
    if request.method=='POST':
        erpid=int(request.form['erpid'])
        password=request.form.get('password')

        user=User.query.filter_by(erp=erpid).first()
        validPass=bcrypt.check_password_hash(user.password,password)
        if(not user or not validPass):
            title="Invalid Cridentials"
            text1="ERP ID and Password Does Not Match"
            link="/login"

            return render_template("common/general.html",
                                   title=title,text1=text1,link=link)
        else:
            login_user(user)
            if(user.role=='Admin'):
                return redirect(url_for('adminDashboard'))
            else:
                return redirect(url_for('userDashboard'))
            
@app.route('/logout',methods=['GET','POST'])
@login_required
def logout():
    if request.method=='GET':
        return render_template('common/logout.html')
    if request.method=='POST':
        if(request.form['logout']=='Yes'):
            logout_user()
            return redirect(url_for('login'))
        else :
            if(current_user.role=='Admin'):
                return redirect(url_for('adminDashboard'))
            else:
                return redirect(url_for('userDashboard'))

#Admin Functions

@app.route('/admin/dashboard',methods=['GET','POST'])
@login_required
def adminDashboard():
    if request.method=='GET':

        count = [
            db.session.query(func.count(Books.isbn)).scalar(),
            db.session.query(func.count(Books.isbn)).filter(Books.available_copies != 0).scalar(),
            db.session.query(func.count(Issued.isbnissue)).filter(Issued.status == 'Issued').scalar(),
            db.session.query(func.count(Issued.isbnissue)).filter(Issued.status == 'Pending').scalar(),
            db.session.query(func.count(User.erp)).scalar()
            ]
        return render_template("admin/dashboard.html",user=current_user,count=count)

@app.route('/admin/allBooks',methods=['GET']) 
@login_required
def allBooks():
    books=db.session.query(Books).order_by(Books.book_name.asc()).all()
    return render_template('admin/allBooks.html',books=books)

@app.route('/admin/addBook',methods=['GET','POST'])
@login_required
def addBook():
    if(request.method=='GET'):
        return render_template('admin/addBook.html')
    if(request.method=='POST'):
        isbn=int(request.form['isbn'])
        name=request.form['name']
        author=request.form['author']
        publication=request.form['publication']
        total_copies=request.form['total_copies']

        # Execute Statement
        exist_check = db.session.query(Books).filter_by(isbn=isbn).first()

        if exist_check:
            title="Book exist"
            text1="ISBN no Already Exist Please Choose New One"
            link="/admin/addBook"
            return render_template('common/general.html',
                                   title=title,text1=text1,link=link)
        
        else:
            new_book=Books(isbn=isbn,book_name=name,author=author,publication=publication,
                           total_copies=total_copies,available_copies=total_copies)
            db.session.add(new_book)
            db.session.commit()
            return redirect(url_for('allBooks'))

@app.route('/admin/viewBook/<isbn>',methods=['GET'])
@login_required
def viewBook(isbn):
    book=db.session.query(Books).filter_by(isbn=isbn).first()
    count = db.session.query(func.count(Issued.isbnissue)).filter_by(isbnissue=isbn).scalar()
    issuers=db.session.execute('''select erp,name,role,date,status 
                               from user,issued_books 
                               where isbnissue= :isbn and erpissue=erp''',
                               {'isbn':isbn})
    return render_template('admin/viewBook.html',book=book,issuers=issuers,count=count)

@app.route('/admin/bookHistory/<isbn>',methods=['GET'])
@login_required
def bookHistory(isbn):
    book=db.session.query(Books).filter_by(isbn=isbn).first()
    issuers=db.session.execute('''select erp,name,role,date,status 
                               from user,history
                               where isbnissue= :isbn and erpissue=erp''',
                               {'isbn':isbn})
    return render_template('admin/bookHistory.html',book=book,issuers=issuers)


@app.route('/admin/updateBook/<isbn>',methods=['GET','POST'])
@login_required
def updateBook(isbn):
    if request.method=='GET':
        book=db.session.query(Books).filter_by(isbn=isbn).first()
        return render_template('admin/updateBook.html',book=book)

    if request.method=='POST':
        book=db.session.query(Books).filter_by(isbn=isbn).first()  
        issuedBooks=book.total_copies-book.available_copies 

        book.book_name=request.form['name']
        book.author=request.form['author']
        book.publication=request.form['publication']  
        book.total_copies=request.form['total_copies']
        book.available_copies=int(request.form['total_copies'])-issuedBooks
        if(book.available_copies<0):
            title='Update Error'
            text1='Available Copies Are Negative Please Enter Correct Total Copies'
            link='/admin/allBooks'
            return render_template('common/general.html',title=title,text1=text1,link=link)
        
        db.session.commit()
        return redirect(url_for('allBooks'))      

@app.route('/admin/deleteBook/<isbn>',methods=['GET','POST'])
@login_required
def deleteBook(isbn):
    if request.method=='GET':
        book=db.session.query(Books).filter_by(isbn=isbn).first()
        if(book.available_copies!=book.total_copies):
            title='Delete Error'
            text1="Can't Delete Book Because Some Copies Are Issued To The Students"
            link='/admin/allBooks'
            return render_template('common/general.html',title=title,text1=text1,link=link)
        return render_template('admin/deleteBook.html',book=book)
    
    if request.method=='POST':
        book=db.session.query(Books).filter_by(isbn=isbn).first()
        db.session.delete(book)
        db.session.commit()
        return redirect(url_for('allBooks'))

@app.route('/admin/allUsers',methods=['GET'])
@login_required
def allUsers():
    users=db.session.query(User).order_by(User.name.asc()).all()
    return render_template('admin/allUsers.html',users=users)

@app.route('/admin/addUser',methods=['GET','POST'])
@login_required
def register():
    if request.method=='GET':
        return render_template('admin/addUser.html')
    if request.method=='POST':
        erpid = int(request.form['erpid'])
        name = request.form['name']
        password = request.form['password']
        password1 = request.form['password1']
        role=request.form['role']

        # Execute Statement
        exist_check = db.session.query(
            User).filter_by(erp=erpid).first()

        if exist_check:
            title="user exist"
            text1="ERP ID Already Exist Please Choose New One"
            link="/admin/addUser"
            return render_template('common/general.html',
                                   title=title,text1=text1,link=link)
        if(password1!=password):
            title="Password Error"
            text1="Password and Confirm Password Should be Same"
            link="/admin/addUser"
            return render_template("common/general.html",
                                   title=title,text1=text1,link=link)
        else:
            hashed_password=bcrypt.generate_password_hash(password)
            new_user = User(erp=erpid,name=name.upper(),password=hashed_password,role=role)
            
            db.session.add(new_user)
            db.session.commit()

            return redirect(url_for('allUsers'))

@app.route('/admin/viewUser/<erp>',methods=['GET'])
@login_required
def viewUser(erp):
    user=db.session.query(User).filter_by(erp=erp).first()
    count = db.session.query(func.count(Issued.erpissue)).filter_by(erpissue=erp).scalar()
    books=db.session.execute('''select isbn,book_name,author,publication,date,status 
                             from books,issued_books 
                             where isbnissue=isbn and erpissue= :erp ''',
                             {'erp':erp} )
    return render_template('admin/viewUser.html',user=user,books=books,count=count)

@app.route('/admin/userHistory/<erp>',methods=['GET'])
@login_required
def userHistory(erp):
    user=db.session.query(User).filter_by(erp=erp).first()
    books=db.session.execute('''select isbn,book_name,author,publication,date,status 
                             from books,history
                             where isbnissue=isbn and erpissue= :erp ''',
                             {'erp':erp} )
    return render_template('admin/userHistory.html',user=user,books=books)   

@app.route('/admin/updateUser/<erp>',methods=['GET','POST'])
@login_required
def updateUser(erp):
    if request.method=='GET':
        user=db.session.query(User).filter_by(erp=erp).first()
        return render_template('admin/updateUser.html',user=user)

    if request.method=='POST':
        user=db.session.query(User).filter_by(erp=erp).first() 
        user.name=(request.form['name']).upper()
        user.role=request.form['role']
        db.session.commit()
        return redirect(url_for('allUsers'))

@app.route('/admin/deleteUser/<erp>',methods=['GET','POST'])
@login_required
def deleteUser(erp):
    if request.method=='GET':
        user=db.session.query(User).filter_by(erp=erp).first()
        issued=db.session.query(Issued).filter_by(erpissue=erp).all()
        if(issued):
            title='Delete Error'
            text1="Can't Delete User Because User Issued Some Books"
            link='/admin/allUsers'
            return render_template('common/general.html',title=title,text1=text1,link=link)
        return render_template('admin/deleteUser.html',user=user)
    
    if request.method=='POST':
        user=db.session.query(User).filter_by(erp=erp).first()
        db.session.delete(user)
        db.session.commit()
        return redirect(url_for('allUsers'))
    
@app.route('/admin/issued_books',methods=['GET','POST'])
@login_required
def issued_books():
    if request.method=='GET':
        books=db.session.execute('''select erp,name,isbn,book_name,author,publication,date 
            from books,issued_books,user
            where isbnissue=isbn and erpissue=erp and status='Issued' 
            order by date asc''')
        return render_template ('admin/issuedBooks.html',books=books)
    
    if request.method=='POST':
        type=request.form['filter']

        if(type=='all_issued'):
            books=db.session.execute('''select erp,name,isbn,book_name,author,publication,date 
            from books,issued_books,user
            where isbnissue=isbn and erpissue=erp and status='Issued' 
            order by date asc''')
            return render_template ('admin/issuedBooks.html',books=books)
        
        if(type=='unavilable'):
            books=db.session.execute('''select isbn,book_name,author,publication
                from books,issued_books
                where isbnissue=isbn and available_copies=0
                order by book_name asc''')
            return render_template('admin/unavilable.html',books=books)

@app.route('/admin/returnBook/<erp>/<isbn>',methods=['GET','POST'])
@login_required
def returnBook(erp,isbn):
    if request.method=='GET':
        user=db.session.query(User).filter_by(erp=erp).first()
        book=db.session.query(Books).filter_by(isbn=isbn).first()

        return render_template('admin/returnBook.html',user=user,book=book)
    
    if request.method=='POST':

        book=db.session.query(Books).filter_by(isbn=isbn).first()
        book.available_copies+=1

        book=db.session.query(Issued).filter_by(erpissue=erp , isbnissue=isbn).first()
        db.session.delete(book)
        db.session.commit()
        today=date.today()
        history = History(issueId=book.issueId, erpissue=erp, isbnissue=isbn, date=today, status='Returned')
        db.session.add(history)
        db.session.commit()
        return redirect(url_for('issued_books'))

@app.route('/admin/issue_request',methods=['GET'])
@login_required
def issueRequest():
    if request.method=='GET':
        books=db.session.execute('''select erp,name,isbn,book_name,author,publication,date 
            from books,issued_books,user
            where isbnissue=isbn and erpissue=erp and status='Pending' 
            order by date asc''')   
        return render_template('admin/issueRequest.html',books=books)

@app.route('/admin/issueBook/<erp>/<isbn>',methods=['GET','POST'])
@login_required
def issueBook(erp,isbn):
    if request.method=='GET':
        user=db.session.query(User).filter_by(erp=erp).first()
        book=db.session.query(Books).filter_by(isbn=isbn).first()
        return render_template('admin/issueBook.html',user=user,book=book)
    
    if request.method=='POST':
        book=db.session.query(Issued).filter_by(erpissue=erp , isbnissue=isbn).first()
        book.status='Issued'
        book.date=date.today()
        db.session.commit()

        return redirect(url_for('issueRequest'))

@app.route('/admin/cancelBook/<erp>/<isbn>',methods=['GET','POST'])
@login_required
def cancelBook(erp,isbn):
    if request.method=='GET':
        user=db.session.query(User).filter_by(erp=erp).first()
        book=db.session.query(Books).filter_by(isbn=isbn).first()
        return render_template('admin/cancelBook.html',user=user,book=book)
    
    if request.method=='POST':
        book=db.session.query(Books).filter_by(isbn=isbn).first()
        book.available_copies+=1
        db.session.commit()

        today=date.today()
        book=db.session.query(Issued).filter_by(erpissue=erp,isbnissue=isbn).first()
        history=History(issueId=book.issueId,erpissue=erp,isbnissue=isbn,date=today,status='Cancelled')
        db.session.add(history)
        db.session.commit()
        db.session.delete(book)
        db.session.commit()

        return redirect(url_for('issueRequest'))        

#User Functions

@app.route('/dashboard/user',methods=['GET'])
@login_required
def userDashboard():
    user=current_user
    erp=user.erp
    books=db.session.execute('''select isbn,book_name,author,publication,date
        from books,issued_books
        where isbnissue=isbn and erpissue= :erp and status='Issued' ''',
        {'erp':erp})
    return render_template("user/dashboard.html",user=user,books=books)

@app.route('/user/allBooks',methods=['GET'])
@login_required
def allBooksUser():
    books=db.session.query(Books).order_by(Books.book_name.asc()).all()
    return render_template('user/allBooks.html',books=books)

@app.route('/user/issueBook/<isbn>',methods=['GET','POST'])
@login_required
def issueBookUser(isbn):
    if request.method=='GET':
        book=db.session.query(Books).filter_by(isbn=isbn).first()
        if book.available_copies==0:
            title='Issue Error'
            text1="Can't Issue Book Because No Copies of Book Are Currently Avilable"
            link='/user/allBooks'
            return render_template('common/general.html',title=title,text1=text1,link=link)
        return render_template('user/issueBook.html',book=book)
    
    if request.method=='POST':
        user=current_user
        erp=user.erp
        issued=db.session.query(Issued).filter_by(erpissue=erp,isbnissue=isbn).first()
        if issued :
            title='Issue Error'
            text1="Can't Issue Book Because It Is Already Issued or Issue Already Requested"
            link='/user/allBooks'
            return render_template('common/general.html',title=title,text1=text1,link=link)
        
        book=db.session.query(Books).filter_by(isbn=isbn).first()
        book.available_copies-=1
        db.session.commit()

        today=date.today()
        new_issue=Issued(erpissue=erp,isbnissue=isbn,date=today,status='Pending')
        db.session.add(new_issue)
        db.session.commit()
        return redirect(url_for('allBooksUser'))

@app.route('/user/issue_request',methods=['GET'])
@login_required
def issueRequestUser():
    erp=current_user.erp
    books=db.session.execute('''select isbn,book_name,author,publication,date
        from books,issued_books
        where isbnissue=isbn and erpissue= :erp and status='Pending' ''',
        {'erp':erp})
    return render_template('user/issueRequest.html',books=books)    

@app.route('/user/cancelBook/<isbn>',methods=['GET','POST'])
@login_required
def cancelBookUser(isbn):
    if request.method=='GET':
        book=db.session.query(Books).filter_by(isbn=isbn).first()
        return render_template('user/cancelBook.html',book=book)

    if request.method=='POST':
        erp=current_user.erp
        book=db.session.query(Books).filter_by(isbn=isbn).first()
        book.available_copies+=1
        db.session.commit()

        book=db.session.query(Issued).filter_by(erpissue=erp,isbnissue=isbn).first()
        
        today=date.today()
        history=History(issueId=book.issueId,erpissue=erp,isbnissue=isbn,date=today,status='Cancelled')
        db.session.add(history)
        db.session.commit()
        db.session.delete(book)
        db.session.commit()

        return redirect(url_for('issueRequestUser'))

@app.route('/user/history',methods=['GET'])
@login_required
def historyUser():

    erp = current_user.erp
    books=db.session.execute('''select isbn,book_name,author,publication,date,status
        from books,history
        where isbnissue=isbn and erpissue= :erp ''',
        {'erp':erp})

    return render_template("user/history.html", user=current_user, books=books)
  

if __name__ == '__main__':
    app.run()
