from datetime import datetime, timezone
from typing import List

from pydantic import ConfigDict
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker
from sqlalchemy_utc import UtcDateTime

from sqlalchemy_to_pydantic import sqlalchemy_to_pydantic

Base = declarative_base()

engine = create_engine("sqlite://", echo=True)


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    fullname = Column(String)
    nickname = Column(String)
    created = Column(DateTime, default=datetime.utcnow)
    updated = Column(UtcDateTime, default=utc_now, onupdate=utc_now)

    addresses = relationship(
        "Address", back_populates="user", cascade="all, delete, delete-orphan"
    )


class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True)
    email_address = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="addresses")


Base.metadata.create_all(engine)


LocalSession = sessionmaker(bind=engine)

db: Session = LocalSession()

ed_user = User(name="ed", fullname="Ed Jones", nickname="edsnickname")

address = Address(email_address="ed@example.com")
address2 = Address(email_address="eddy@example.com")
ed_user.addresses = [address, address2]
db.add(ed_user)
db.commit()


def test_defaults() -> None:
    PydanticUser = sqlalchemy_to_pydantic(User)
    PydanticAddress = sqlalchemy_to_pydantic(Address)

    class PydanticUserWithAddresses(PydanticUser):
        addresses: List[PydanticAddress] = []

    user = db.query(User).first()
    pydantic_user = PydanticUser.model_validate(user)
    data = pydantic_user.model_dump()
    assert isinstance(data["created"], datetime)
    assert isinstance(data["updated"], datetime)
    check_data = data.copy()
    del check_data["created"]
    del check_data["updated"]
    assert check_data == {
        "fullname": "Ed Jones",
        "id": 1,
        "name": "ed",
        "nickname": "edsnickname",
    }
    pydantic_user_with_addresses = PydanticUserWithAddresses.model_validate(user)
    data = pydantic_user_with_addresses.model_dump()
    assert isinstance(data["updated"], datetime)
    assert isinstance(data["created"], datetime)
    check_data = data.copy()
    del check_data["updated"]
    del check_data["created"]
    assert check_data == {
        "fullname": "Ed Jones",
        "id": 1,
        "name": "ed",
        "nickname": "edsnickname",
        "addresses": [
            {"email_address": "ed@example.com", "id": 1, "user_id": 1},
            {"email_address": "eddy@example.com", "id": 2, "user_id": 1},
        ],
    }


def test_schema() -> None:
    PydanticUser = sqlalchemy_to_pydantic(User)
    PydanticAddress = sqlalchemy_to_pydantic(Address)

    assert PydanticUser.model_json_schema() == {
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "name": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "default": None,
                "title": "Name",
            },
            "fullname": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "default": None,
                "title": "Fullname",
            },
            "nickname": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "default": None,
                "title": "Nickname",
            },
            "created": {
                "anyOf": [{"format": "date-time", "type": "string"}, {"type": "null"}],
                "default": None,
                "title": "Created",
            },
            "updated": {
                "anyOf": [{"format": "date-time", "type": "string"}, {"type": "null"}],
                "default": None,
                "title": "Updated",
            },
        },
        "required": ["id"],
        "title": "User",
        "type": "object",
    }
    assert PydanticAddress.model_json_schema() == {
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "email_address": {"title": "Email Address", "type": "string"},
            "user_id": {
                "anyOf": [{"type": "integer"}, {"type": "null"}],
                "default": None,
                "title": "User Id",
            },
        },
        "required": ["id", "email_address"],
        "title": "Address",
        "type": "object",
    }


def test_config() -> None:
    def to_camel_case(string: str) -> str:
        pascal_case = "".join(word.capitalize() for word in string.split("_"))
        camel_case = pascal_case[0].lower() + pascal_case[1:]
        return camel_case

    config = ConfigDict(from_attributes=True, alias_generator=to_camel_case)

    PydanticUser = sqlalchemy_to_pydantic(User)
    PydanticAddress = sqlalchemy_to_pydantic(Address, config=config)

    class PydanticUserWithAddresses(PydanticUser):
        addresses: List[PydanticAddress] = []

    user = db.query(User).first()
    pydantic_user_with_addresses = PydanticUserWithAddresses.model_validate(user)
    data = pydantic_user_with_addresses.model_dump(by_alias=True)
    assert isinstance(data["created"], datetime)
    assert isinstance(data["updated"], datetime)
    check_data = data.copy()
    del check_data["created"]
    del check_data["updated"]
    assert check_data == {
        "fullname": "Ed Jones",
        "id": 1,
        "name": "ed",
        "nickname": "edsnickname",
        "addresses": [
            {"emailAddress": "ed@example.com", "id": 1, "userId": 1},
            {"emailAddress": "eddy@example.com", "id": 2, "userId": 1},
        ],
    }


def test_exclude() -> None:
    PydanticUser = sqlalchemy_to_pydantic(User, exclude={"nickname"})
    PydanticAddress = sqlalchemy_to_pydantic(Address, exclude={"user_id"})

    class PydanticUserWithAddresses(PydanticUser):
        addresses: List[PydanticAddress] = []

    user = db.query(User).first()
    print(user.addresses)
    pydantic_user_with_addresses = PydanticUserWithAddresses.model_validate(user)
    data = pydantic_user_with_addresses.model_dump(by_alias=True)
    assert isinstance(data["created"], datetime)
    assert isinstance(data["updated"], datetime)
    check_data = data.copy()
    del check_data["created"]
    del check_data["updated"]
    assert check_data == {
        "fullname": "Ed Jones",
        "id": 1,
        "name": "ed",
        "addresses": [
            {"email_address": "ed@example.com", "id": 1},
            {"email_address": "eddy@example.com", "id": 2},
        ],
    }