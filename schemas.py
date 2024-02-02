from pydantic import BaseModel


class Course(BaseModel):
    direction: str
    value: float


class CourseList(BaseModel):
    exchanger: str
    courses: list[Course]
