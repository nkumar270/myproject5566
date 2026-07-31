import os
import unittest
# Set environment variables before importing library to use an in-memory SQLite database
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"

# Ensure no emails are actually sent during testing
os.environ["MAIL_SERVER"] = "localhost"
os.environ["MAIL_PORT"] = "8025"

from library import library, db, Book, Student, IssueBook, users, librarian
from datetime import datetime, timedelta

class TestLibraryApp(unittest.TestCase):
    def setUp(self):
        # Set up test client
        self.app = library.test_client()
        self.app.testing = True

        # Create a fresh database for each test
        with library.app_context():
            db.create_all()

    def tearDown(self):
        # Drop all tables after each test
        with library.app_context():
            db.session.remove()
            db.drop_all()

    def test_database_creation(self):
        """Verify models can be saved and retrieved, and __repr__ functions work correctly."""
        with library.app_context():
            # Test Book model
            b = Book(Title="The Hobbit", Category="Fantasy", Author="Tolkien", Quantity=5)
            db.session.add(b)
            db.session.commit()

            # Verify book
            retrieved_book = Book.query.filter_by(Title="The Hobbit").first()
            self.assertIsNotNone(retrieved_book)
            self.assertEqual(retrieved_book.Quantity, 5)
            self.assertEqual(repr(retrieved_book), "Book The Hobbit")

            # Test Student model
            s = Student(Roll_no=101, name="John Doe", email="john@example.com", password="pass")
            db.session.add(s)
            db.session.commit()

            retrieved_student = Student.query.filter_by(Roll_no=101).first()
            self.assertIsNotNone(retrieved_student)
            self.assertEqual(retrieved_student.name, "John Doe")
            self.assertEqual(repr(retrieved_student), "Student John Doe")

            # Test IssueBook model
            issue = IssueBook(student_id=s.id, book_id=b.id, issue_date=datetime.utcnow())
            db.session.add(issue)
            db.session.commit()

            retrieved_issue = IssueBook.query.first()
            self.assertIsNotNone(retrieved_issue)
            self.assertEqual(retrieved_issue.student_id, s.id)
            self.assertEqual(retrieved_issue.book_id, b.id)
            self.assertEqual(repr(retrieved_issue), f"IssueBook {retrieved_issue.id}")

    def test_home_and_index_routes(self):
        """Verify home, index, and simple routes render correctly."""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Welcome", response.data)

        response_index = self.app.get('/index')
        self.assertEqual(response_index.status_code, 200)
        self.assertIn(b"Login with", response_index.data)

    def test_add_and_view_book_routes(self):
        """Verify a book can be added via /addbook and viewed via /view."""
        # POST to add a new book
        response = self.app.post('/addbook', data={
            "Title": "1984",
            "Category": "Dystopian",
            "Author": "George Orwell",
            "Quantity": "10"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"1984", response.data)

        # GET view to make sure book is there
        response_view = self.app.get('/view')
        self.assertEqual(response_view.status_code, 200)
        self.assertIn(b"George Orwell", response_view.data)

    def test_update_and_delete_book_routes(self):
        """Verify we can update and delete books."""
        with library.app_context():
            b = Book(Title="Old Title", Category="Cat", Author="Auth", Quantity=2)
            db.session.add(b)
            db.session.commit()
            book_id = b.id

        # Update the book
        response_update = self.app.post(f'/update_book/{book_id}', data={
            "Title": "New Title",
            "Category": "New Cat",
            "Author": "New Auth",
            "Quantity": "3"
        }, follow_redirects=True)
        self.assertEqual(response_update.status_code, 200)
        self.assertIn(b"New Title", response_update.data)

        # Delete the book
        response_delete = self.app.post(f'/delete_book/{book_id}', follow_redirects=True)
        self.assertEqual(response_delete.status_code, 200)
        self.assertNotIn(b"New Title", response_delete.data)

    def test_issue_and_return_book_flow(self):
        """Verify issuing a book decrements quantity and returning increments it."""
        with library.app_context():
            b = Book(Title="Moby Dick", Category="Adventure", Author="Herman Melville", Quantity=1)
            s = Student(Roll_no=202, name="Jane Doe", email="jane@example.com", password="pwd")
            db.session.add_all([b, s])
            db.session.commit()
            book_id = b.id
            student_id = s.id

        # Issue the book
        response_issue = self.app.post('/Issue_book', data={
            "student_id": str(student_id),
            "book_id": str(book_id)
        }, follow_redirects=True)
        self.assertEqual(response_issue.status_code, 200)

        with library.app_context():
            # Book quantity should be 0 now
            retrieved_book = Book.query.get(book_id)
            self.assertEqual(retrieved_book.Quantity, 0)

            # An IssueBook record should exist
            issue = IssueBook.query.filter_by(student_id=student_id, book_id=book_id).first()
            self.assertIsNotNone(issue)
            self.assertIsNone(issue.return_date)

        # Return the book (No penalty)
        response_return = self.app.post('/return_book', data={
            "student_id": str(student_id),
            "book_id": str(book_id)
        }, follow_redirects=True)
        self.assertEqual(response_return.status_code, 200)

        with library.app_context():
            # Book quantity should be 1 again
            retrieved_book = Book.query.get(book_id)
            self.assertEqual(retrieved_book.Quantity, 1)

            # Issue record should be deleted since penalty is 0
            issue = IssueBook.query.filter_by(student_id=student_id, book_id=book_id).first()
            self.assertIsNone(issue)

    def test_return_book_with_penalty(self):
        """Verify return_book logic correctly calculates and saves penalty when returned late."""
        with library.app_context():
            b = Book(Title="Moby Dick", Category="Adventure", Author="Herman Melville", Quantity=1)
            s = Student(Roll_no=202, name="Jane Doe", email="jane@example.com", password="pwd")
            db.session.add_all([b, s])
            db.session.commit()
            book_id = b.id
            student_id = s.id

            # Issue with an issue_date in the past (e.g., 20 days ago)
            past_date = datetime.utcnow() - timedelta(days=20)
            issue = IssueBook(student_id=student_id, book_id=book_id, issue_date=past_date)
            b.Quantity -= 1
            db.session.add(issue)
            db.session.commit()

        # Return the book
        response_return = self.app.post('/return_book', data={
            "student_id": str(student_id),
            "book_id": str(book_id)
        }, follow_redirects=True)
        self.assertEqual(response_return.status_code, 200)
        self.assertIn(b"Pay your penalty first", response_return.data)

        with library.app_context():
            # Quantity should still be updated (since they brought the book back)
            retrieved_book = Book.query.get(book_id)
            self.assertEqual(retrieved_book.Quantity, 1)

            # The issue record should still exist to record the penalty
            issue = IssueBook.query.filter_by(student_id=student_id, book_id=book_id).first()
            self.assertIsNotNone(issue)
            self.assertIsNotNone(issue.return_date)
            # Allowed days: 15. Late by 5 days. Penalty rate: 5 per day. Expected penalty: 25.
            self.assertEqual(issue.penalty, 25.0)

    def test_student_module_login_logout_and_return_book(self):
        """Verify student session login, logout, dynamic penalty viewing, return, and penalty payment."""
        with library.app_context():
            b = Book(Title="Frankenstein", Category="Sci-Fi", Author="Mary Shelley", Quantity=1)
            s = Student(Roll_no=303, name="Student User", email="student@example.com", password="pwd")
            db.session.add_all([b, s])
            db.session.commit()
            book_id = b.id
            student_id = s.id

        # 1. Try to view student issued books without login
        response = self.app.get('/student_issued', follow_redirects=True)
        self.assertIn(b"Please login first", response.data)

        # 2. Login successfully
        response_login = self.app.post('/student_login', data={
            "email": "student@example.com",
            "password": "pwd"
        }, follow_redirects=True)
        self.assertIn(b"Login Successful", response_login.data)
        self.assertIn(b"Welcome to our Library as Student", response_login.data)

        # 3. Issue a book to this student using the main Issue_book route
        with library.app_context():
            issue = IssueBook(student_id=student_id, book_id=book_id, issue_date=datetime.utcnow() - timedelta(days=20))
            db.session.add(issue)
            db.session.commit()
            issue_id = issue.id

        # 4. View student issued list with estimated penalty
        response_issued = self.app.get('/student_issued')
        self.assertEqual(response_issued.status_code, 200)
        self.assertIn(b"Est. Penalty: 25", response_issued.data)
        self.assertIn(b"Return Book", response_issued.data)

        # 5. Return book via student module return route
        response_return = self.app.post(f'/student_return_book/{issue_id}', follow_redirects=True)
        self.assertIn(b"Book returned! Please pay your penalty of 25.0", response_return.data)

        with library.app_context():
            # Check book quantity is incremented
            retrieved_book = Book.query.get(book_id)
            self.assertEqual(retrieved_book.Quantity, 2)

            # Issue book should record return date and exact penalty
            retrieved_issue = IssueBook.query.get(issue_id)
            self.assertIsNotNone(retrieved_issue)
            self.assertIsNotNone(retrieved_issue.return_date)
            self.assertEqual(retrieved_issue.penalty, 25.0)

        # 6. Verify "Pay Penalty" button is visible
        response_issued_post_return = self.app.get('/student_issued')
        self.assertIn(b"Pay Penalty", response_issued_post_return.data)

        # 7. Pay Penalty via student module pay penalty route
        response_pay = self.app.post(f'/student_pay_penalty/{issue_id}', follow_redirects=True)
        self.assertIn(b"Penalty paid successfully!", response_pay.data)

        with library.app_context():
            # Issue book should be deleted after penalty payment
            retrieved_issue = IssueBook.query.get(issue_id)
            self.assertIsNone(retrieved_issue)

        # 8. Logout
        response_logout = self.app.get('/student_logout', follow_redirects=True)
        self.assertIn(b"Logged out successfully", response_logout.data)

if __name__ == '__main__':
    unittest.main()
