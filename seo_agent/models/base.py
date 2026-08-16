"""Base Pydantic model for SEO Agent domain and API schemas.

Provides a common foundation for all Pydantic v2 models in the SEO Agent codebase,
ensuring consistent serialization, immutability defaults, type coercion,
positional-argument initialization support, and dataclass backward compatibility.
"""

from __future__ import annotations

from dataclasses import Field as DataclassField, _FIELD, _MISSING_TYPE
from pathlib import PurePath
from typing import Any, Self, TypeVar
from pydantic import BaseModel, ConfigDict, model_validator
from pydantic_core import PydanticUndefined

T = TypeVar("T", bound="BasePydanticModel")


def _is_str_field(annotation: Any) -> bool:
    """Check if a field annotation expects str (and not Path/PurePath)."""
    if isinstance(annotation, type) and issubclass(annotation, str):
        return True
    from typing import get_args
    args = get_args(annotation)
    if args:
        has_str = any(
            isinstance(a, type) and issubclass(a, str)
            for a in args
            if isinstance(a, type)
        )
        has_path = any(
            isinstance(a, type) and issubclass(a, PurePath)
            for a in args
            if isinstance(a, type)
        )
        return has_str and not has_path
    return False


class BasePydanticModel(BaseModel):
    """Base Pydantic v2 model for SEO Agent schemas.

    Attributes:
        model_config: Default configuration for all derived Pydantic models.
            - populate_by_name: Allows instantiating using alias or field names.
            - arbitrary_types_allowed: Allows custom non-Pydantic types when needed.
            - validate_assignment: Validates attributes if mutated.
            - use_enum_values: Keeps enum instances by default (False) for type safety.
            - extra: "ignore" by default to tolerate extra unexpected payload fields safely.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_path_to_str(cls, data: Any) -> Any:
        """Coerce Path / PurePath objects to strings ONLY for fields annotated as str."""
        if isinstance(data, dict):
            new_data = dict(data)
            for k, v in data.items():
                if isinstance(v, PurePath):
                    field_info = cls.model_fields.get(k)
                    if field_info is not None and _is_str_field(field_info.annotation):
                        new_data[k] = str(v)
            return new_data
        return data

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize model supporting both positional and keyword arguments for dataclass compatibility."""
        if args:
            field_names = list(self.__class__.model_fields.keys())
            for idx, arg in enumerate(args):
                if idx < len(field_names):
                    kw = field_names[idx]
                    if kw not in kwargs:
                        field_info = self.__class__.model_fields.get(kw)
                        if field_info is not None and _is_str_field(field_info.annotation) and isinstance(arg, PurePath):
                            kwargs[kw] = str(arg)
                        else:
                            kwargs[kw] = arg
        super().__init__(**kwargs)

        # Populate __dataclass_fields__ on class if not present for dataclasses.asdict compatibility
        cls = self.__class__
        if "__dataclass_fields__" not in cls.__dict__:
            fields_dict: dict[str, Any] = {}
            for name, field_info in cls.model_fields.items():
                default_val = (
                    field_info.default
                    if field_info.default is not PydanticUndefined
                    else _MISSING_TYPE
                )
                default_factory = (
                    field_info.default_factory
                    if field_info.default_factory is not None
                    else _MISSING_TYPE
                )
                f = DataclassField(
                    default=default_val,
                    default_factory=default_factory,
                    init=True,
                    repr=True,
                    hash=None,
                    compare=True,
                    metadata={},
                    kw_only=False,
                )
                f.name = name
                f._field_type = _FIELD
                f.type = field_info.annotation
                fields_dict[name] = f
            cls.__dataclass_fields__ = fields_dict

    def to_dict(self, mode: str = "python", by_alias: bool = False) -> dict[str, Any]:
        """Convert model to dictionary payload.

        Args:
            mode: 'python' (preserves Python objects like Path, datetime) or 'json' (primitives).
            by_alias: Use field aliases if defined.

        Returns:
            Dictionary representation of the model.
        """
        return self.model_dump(mode=mode, by_alias=by_alias)

    def to_json(self, indent: int | None = None, by_alias: bool = False) -> str:
        """Serialize model to JSON string.

        Args:
            indent: Optional indentation for pretty printing.
            by_alias: Use field aliases if defined.

        Returns:
            JSON string representation.
        """
        return self.model_dump_json(indent=indent, by_alias=by_alias)

    def replace(self, **kwargs: Any) -> Self:
        """Dataclass-compatible replace helper using model_copy.

        Args:
            **kwargs: Field updates to apply.

        Returns:
            A new instance with updated fields.
        """
        return self.model_copy(update=kwargs)

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        """Construct model from a dictionary.

        Args:
            data: Input dictionary payload.

        Returns:
            Instance of the model class.
        """
        return cls.model_validate(data)
