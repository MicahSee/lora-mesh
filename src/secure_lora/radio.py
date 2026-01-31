from dataclasses import dataclass
from typing import Any, Callable, Literal


@dataclass
class RadioParameter:
    """Describes a tunable radio parameter for UI generation."""
    name: str
    param_type: Literal["int", "float", "enum", "bool"]
    valid_values: list | tuple  # enum options or (min, max) range
    unit: str | None = None
    description: str = ""
    step: float | None = None  # step size for numeric types
    readonly: bool = False


def radio_param(
    param_type: Literal["int", "float", "enum", "bool"],
    valid_values: list | tuple,
    unit: str | None = None,
    description: str = "",
    step: float | None = None,
    readonly: bool = False,
) -> Callable:
    """
    Decorator to register a property as a tunable radio parameter.

    Usage:
        @radio_param("int", (400, 960), unit="MHz", description="Carrier frequency")
        @property
        def frequency(self) -> int:
            return self._frequency

        @frequency.setter
        def frequency(self, value: int):
            self._frequency = value
    """
    def decorator(func: Callable) -> Callable:
        func._radio_param_meta = RadioParameter(
            name=func.__name__,
            param_type=param_type,
            valid_values=valid_values,
            unit=unit,
            description=description,
            step=step,
            readonly=readonly,
        )
        return func
    return decorator


class RadioInterface:
    """
    Base class for radio hardware interfaces.

    Subclasses should implement send/receive and use @radio_param decorator
    on properties to expose tunable parameters for UI generation.
    """

    def send(self, data: bytes) -> None:
        """Send data over the radio."""
        raise NotImplementedError

    def receive(self) -> bytes | None:
        """Receive data from the radio. Returns None if no data available."""
        raise NotImplementedError

    @classmethod
    def get_parameter_definitions(cls) -> list[RadioParameter]:
        """
        Returns list of all tunable parameters defined on this radio class.
        Introspects the class for properties decorated with @radio_param.
        """
        params = []
        for name in dir(cls):
            try:
                attr = getattr(cls, name)
                # Check if it's a property with our metadata
                if isinstance(attr, property) and hasattr(attr.fget, '_radio_param_meta'):
                    params.append(attr.fget._radio_param_meta)
            except AttributeError:
                continue
        return params

    def get_parameters(self) -> dict[str, Any]:
        """Returns current values of all tunable parameters."""
        result = {}
        for param in self.get_parameter_definitions():
            result[param.name] = getattr(self, param.name)
        return result

    def set_parameter(self, name: str, value: Any) -> None:
        """
        Set a parameter by name with validation.

        Raises:
            ValueError: If parameter doesn't exist or value is invalid.
        """
        param_defs = {p.name: p for p in self.get_parameter_definitions()}
        if name not in param_defs:
            raise ValueError(f"Unknown parameter: {name}")

        param = param_defs[name]
        if param.readonly:
            raise ValueError(f"Parameter '{name}' is read-only")

        # Validate value
        self._validate_param_value(param, value)
        setattr(self, name, value)

    def _validate_param_value(self, param: RadioParameter, value: Any) -> None:
        """Validate a value against parameter constraints."""
        if param.param_type == "bool":
            if not isinstance(value, bool):
                raise ValueError(f"Parameter '{param.name}' must be a boolean")

        elif param.param_type == "enum":
            if value not in param.valid_values:
                raise ValueError(
                    f"Parameter '{param.name}' must be one of {param.valid_values}"
                )

        elif param.param_type in ("int", "float"):
            if not isinstance(value, (int, float)):
                raise ValueError(f"Parameter '{param.name}' must be numeric")

            min_val, max_val = param.valid_values
            if not (min_val <= value <= max_val):
                raise ValueError(
                    f"Parameter '{param.name}' must be between {min_val} and {max_val}"
                )

            if param.param_type == "int" and not isinstance(value, int):
                raise ValueError(f"Parameter '{param.name}' must be an integer")
