from flask import Flask, render_template, redirect,request,flash,url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz
from sqlalchemy import ForeignKey

library=Flask(__name__,static_folder="static",static_url_path="/static")

library.config["SQLALCHEMY_DATABASE_URI"]="sqlite:///data.db"
library.config["SQLALCHEMY_TRACK-MODIFICATIONS"]=False

library.secret_key = "1234"


db= SQLAlchemy(library)

def indian_time():
   india=pytz.timezone('Asia/KOLKATA')
   return datetime.now(india)

class users(db.Model):
   id=db.Column(db.Integer, primary_key=True)
   name=db.Column(db.String(50), nullable = False)
   email=db.Column(db.String(50),unique=True)
   password=db.Column(db.String(50))

class librarian(db.Model):
   id=db.Column(db.Integer, primary_key=True)
   name=db.Column(db.String(50), nullable = False)
   email=db.Column(db.String(50),unique=True)
   password=db.Column(db.String(50), nullable=False)

class Book(db.Model):
   __tablename__="book"
   id=db.Column(db.Integer, primary_key=True)
   Title=db.Column(db.String(50),nullable=False)
   Category=db.Column(db.String(50),nullable=False) 
   Author=db.Column(db.String(50),nullable=False) 
   Quantity=db.Column(db.Integer)
   issues= db.relationship('IssueBook', backref='user', lazy=True) 

   def __repr__(self):
      return f"Book {self.name}"

class Student(db.Model):
   __tablename__="student"
   id=db.Column(db.Integer, primary_key=True)
   Roll_no=db.Column(db.Integer, nullable=False)
   name=db.Column(db.String(100),nullable=False)
   email=db.Column(db.String(120),unique=True)
   password=db.Column(db.String(50), nullable=False)
   is_active=db.Column(db.Boolean,default=True)
   issues= db.relationship('IssueBook', backref='Book', lazy=True)
   
   def __repr__(self):
    return f"Student {self.name}"
   
class IssueBook(db.Model):
   __tablename__="IssueBooks"
   id=db.Column(db.Integer, primary_key=True)
   student_id=db.Column(db.Integer, ForeignKey('student.id'), nullable=False)
   book_id=db.Column(db.Integer, ForeignKey('book.id'), nullable=False)
   issue_date=db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
   
   def __repr__(self):
    return f"IssueBook {self.name}"
   
with library.app_context():
   db.create_all()



@library.route("/index")
def index():
   return render_template("index.html")

@library.route("/")
def home():
     username = request.args.get("username", "Guest")
     return render_template("home.html",name=username)

@library.route("/register", methods=["GET","POST"])
def register():
   if request.method=="POST":
      form_username = request.form.get("username")
      form_email = request.form.get("email")
      form_password = request.form.get("password")
      print(form_email, form_password, form_username)

      new_user=users(
         email= form_email,
         password= form_password,
         name= form_username     
      )
      db.session.add(new_user)
      db.session.commit()
      flash("Account Created :")
      return redirect(url_for("login"))
   
   return render_template("register.html")


@library.route("/login", methods=["GET","POST"])
def login():
   if request.method=="POST":
       form_email = request.form.get("email")
       form_password = request.form.get("password")

       current_user= users.query.filter_by(email=form_email).first()
       if current_user and current_user.password==form_password:
          flash("Login Successful :")
          return redirect(url_for('index'))
       
       flash("Invalid credentails :")
       return redirect(url_for('login')) 
   else:  
       return render_template("login.html")
 
@library.route("/loginlib", methods=["GET","POST"])
def loginlib():
   if request.method=="POST":
       form_email = request.form.get("email")
       form_password = request.form.get("password")

       current_user= librarian.query.filter_by(email=form_email).first()
       if current_user and current_user.password== form_password:
          flash("Login Successful :")
          return redirect(url_for('home',username=current_user.name))
       
       flash("Invalid credentails :")
       return redirect(url_for('loginlib')) 
   else:  
      return render_template("loginlib.html")


@library.route("/registerlib",methods=["GET","POST"])
def registerlib():
   if request.method=="POST":
      form_username = request.form.get("username")
      form_email = request.form.get("email")
      form_password = request.form.get("password")
      print(form_email, form_password, form_username)

      new_user=librarian(
         email= form_email,
         password= form_password,
         name= form_username     
      )
      db.session.add(new_user)
      db.session.commit()
      flash("Account Created :")
      return redirect(url_for("loginlib.html"))
   
   return render_template("registerlib.html")

@library.route("/addbook",methods=["GET","POST"])
def addbook():
   if request.method=="POST":
      form_Title=request.form.get("Title")
      form_Category=request.form.get("Category")
      form_Author=request.form.get("Author")
      form_Quantity=request.form.get("Quantity")
      print(form_Title, form_Category, form_Author, form_Quantity)

      new_book=Book(
         Title=form_Title,
         Category=form_Category,
         Author=form_Author,
         Quantity=form_Quantity
      )

      db.session.add(new_book)
      db.session.commit()
      flash("Book Add Successfully :")
      return redirect(url_for('view_book'))      
   
   return render_template("addbook.html")

@library.route("/view", methods=["GET","POST"])
def view_book():
   books=Book.query.all()
   return render_template("view.html",books=books)

@library.route('/update_book/<int:id>', methods=["GET", "POST"])
def update_book(id):
    book = Book.query.get_or_404(id)

    if request.method == "POST":
        book.Title = request.form['Title']
        book.Category = request.form['Category']
        book.Author = request.form['Author']
        book.Quantity = request.form['Quantity']

        db.session.commit()

        flash("Book updated successfully!", "success")
        return redirect(url_for('view_book'))

    return render_template('updatebook.html', book=book)

@library.route('/delete_book/<int:id>', methods=["POST","GET"])
def delete_book(id):
    book = Book.query.get_or_404(id)

    db.session.delete(book)
    db.session.commit()

    flash("Book deleted successfully!", "success")
    return redirect(url_for('view_book'))

@library.route("/student",methods=["GET","POST"])
def student():
   if request.method=="POST":
      form_Roll_no = request.form.get("Roll_no")
      form_name = request.form.get("name")
      form_email = request.form.get("email")
      form_password = request.form.get("password")
      form_is_active = request.form.get("is_active")

      new_user=Student(
         Roll_no= form_Roll_no,
         name= form_name,
         email= form_email,
         password= form_password,
         is_active= form_is_active  
      )
      db.session.add(new_user)
      db.session.commit()
      flash("Account Created :")
      return redirect(url_for("student_login"))
   
   return render_template("student.html")

@library.route("/student_login", methods=["GET","POST"])
def student_login():
   if request.method=="POST":
      form_email = request.form.get("email")
      form_password = request.form.get("password")

      current_user= Student.query.filter_by(email=form_email).first()
      if current_user and current_user.password== form_password:
          flash("Login Successful :")
          return redirect(url_for('home1',username=current_user.name))
       
      flash("Invalid credentails :")
      return redirect(url_for('student_login')) 
   else:  
      return render_template("student_login.html")


@library.route("/home1")
def home1():
   username = request.args.get("username", "Guest")
   return render_template("home1.html",name=username)


if __name__=="__main__":
 library.run(debug=True, use_reloader=True)