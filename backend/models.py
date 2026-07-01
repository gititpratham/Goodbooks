from sqlalchemy import Column, Integer, String, Float, Text
from database import Base

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary key=True, index=True)
    book_id = Column(Integer, unique=True, index=True)
    title = Column(String(255), nullable=False)
    authors = Column(Text, nullable=False)  # Stores string representation of authors list
    average_rating = Column(Float, default=0.0)
    description = Column(Text, nullable=True)
    genres = Column(Text, nullable=True)  # Stores string representation of genres list
    image_url = Column(Text, nullable=True)
    pages = Column(Integer, nullable=True)
    publish_date = Column(String(50), nullable=True)
    ratings_count = Column(Integer, default=0)

    def to_dict(self):
        """Converts the Book model instance to a dictionary."""
        return {
            "id": self.id,
            "book_id": self.book_id,
            "title": self.title,
            "authors": self.authors,
            "average_rating": self.average_rating,
            "description": self.description,
            "genres": self.genres,
            "image_url": self.image_url,
            "pages": self.pages,
            "publish_date": self.publish_date,
            "ratings_count": self.ratings_count,
        }
