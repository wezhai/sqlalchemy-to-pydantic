from typing import Container, Optional, Type

from pydantic import BaseModel, ConfigDict, create_model

orm_config = ConfigDict(from_attributes=True)

def sqlalchemy_to_pydantic(
    db_model: Type, *, config: Type = orm_config, exclude: Container[str] = []
) -> Type[BaseModel]:
    table = db_model.metadata.tables[db_model.__tablename__]
    fields = {}
    for column in table.columns:
        name = column.name
        if name in exclude:
            continue
        python_type: Optional[type] = None
        if hasattr(column.type, "impl"):
            if hasattr(column.type.impl, "python_type"):
                python_type = column.type.impl.python_type
        elif hasattr(column.type, "python_type"):
            python_type = column.type.python_type
        assert python_type, f"Could not infer python_type for {column}"

        if not column.nullable:
            fields[name] = (python_type, ...)
        else:
            fields[name] = (Optional[python_type], None)

    pydantic_model = create_model(db_model.__name__, __config__=config, **fields)
    return pydantic_model
