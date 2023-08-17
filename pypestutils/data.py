"""Data module."""
from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt

__all__ = ["ManyArrays", "validate_scalar"]


def validate_scalar(name: str, value: Any, **kwargs) -> None:
    """Validate scalar value according to supported kwargs.

    Parameters
    ----------
    name : str
        Name of parameter, used for error message.
    value : any
        Value of parameter.
    kwargs : dict
        Supported validation keywords are: isfinite, gt, ge, lt, le, isin and
        enum.

    Raises
    ------
    ValueError
        When value fails validation criteria.
    NotImplementedError
        When keyword is not recognized.
    """
    if not np.isscalar(value):
        raise ValueError(f"'{name}' is not a scalar value")
    if "isfinite" in kwargs:
        assert kwargs.pop("isfinite") is True
        if not np.isfinite(value):
            raise ValueError(f"'{name}' must be finite (was {value!r})")
    if "gt" in kwargs:
        gt = kwargs.pop("gt")
        if not (value > gt):
            raise ValueError(f"'{name}' must be greater than {gt} (was {value!r})")
    if "ge" in kwargs:
        ge = kwargs.pop("ge")
        if not (value >= ge):
            raise ValueError(
                f"'{name}' must be greater than or equal to {ge} (was {value!r})"
            )
    if "lt" in kwargs:
        lt = kwargs.pop("lt")
        if not (value < lt):
            raise ValueError(f"'{name}' must be less than {lt} (was {value!r})")
    if "le" in kwargs:
        le = kwargs.pop("le")
        if not (value <= le):
            raise ValueError(
                f"'{name}' must be less than or equal to {le} (was {value!r})"
            )
    if "isin" in kwargs:
        isin = kwargs.pop("isin")
        if not np.isin(value, isin):
            raise ValueError(f"'{name}' must be in {isin} (was {value!r})")
    if "enum" in kwargs:
        enum_v = kwargs.pop("enum")
        valid_options = enum_v.get_valid_options()
        if not np.isin(value, list(valid_options.keys())):
            enum_str = ", ".join([f"{v} ({n})" for (v, n) in valid_options.items()])
            raise ValueError(
                f"'{name}' must be in enum {enum_v.__name__} {enum_str} (was {value!r})"
            )
    if kwargs:
        raise NotImplementedError(f"unhandled kwargs {kwargs}")


class ManyArrays:
    """Gather and check arrays and, if needed, fill-out scalars.

    All arrays are 1D with the same shape (or length). Float arrays are always
    float64, and integer arrays are always int32. All arrays are contiguous.
    This class is used as a pre-processor input for ctypes.

    Parameters
    ----------
    float_arrays : dict of array_like, optional
        Dict of 1D arrays, assume to have same shape.
    float_any : dict of array_like or float, optional
        Dict of float or 1D arrays.
    int_any : dict of array_like or int, optional
        Dict of int or 1D arrays.
    ar_len : int, optional
        If specified, this is used for the expected array size and shape.
    """

    shape = ()  # type: tuple | tuple[int]
    _names = []  # type: list[str]

    def __init__(
        self,
        float_arrays: dict[str, npt.ArrayLike] = {},
        float_any: dict[str, float | npt.ArrayLike] = {},
        int_any: dict[str, int | npt.ArrayLike] = {},
        ar_len: int | None = None,
    ) -> None:
        self._names = []
        # find common array size
        if ar_len is not None:
            if not isinstance(ar_len, int):
                raise TypeError("'ar_len' must be int")
            self.shape = (ar_len,)
        for name in float_arrays.keys():
            if name in self._names:
                raise KeyError(f"'{name}' defined more than once")
            self._names.append(name)
            # Each must be 1D and the same shape
            ar = np.array(float_arrays[name], np.float64, order="F", copy=False)
            if ar.ndim != 1:
                raise ValueError(f"expected '{name}' ndim to be 1; found {ar.ndim}")
            if not self.shape:
                self.shape = ar.shape
            elif ar.shape != self.shape:
                raise ValueError(
                    f"expected '{name}' shape to be {self.shape}; found {ar.shape}"
                )
            setattr(self, name, ar)
        for name in float_any.keys():
            if name in self._names:
                raise KeyError(f"'{name}' defined more than once")
            self._names.append(name)
            float_any[name] = ar = np.array(
                float_any[name], np.float64, order="F", copy=False
            )
            if not self.shape and ar.ndim == 1:
                self.shape = ar.shape
        for name in int_any.keys():
            if name in self._names:
                raise KeyError(f"'{name}' defined more than once")
            self._names.append(name)
            int_any[name] = ar = np.array(int_any[name], order="F", copy=False)
            if not self.shape and ar.ndim == 1:
                self.shape = ar.shape
        if not self.shape:
            self.shape = (1,)  # if all scalars, assume this size
        for name in float_any.keys():
            ar = float_any[name]
            if ar.ndim == 0:
                ar = np.full(self.shape, ar)
            elif ar.ndim != 1:
                raise ValueError(f"expected '{name}' ndim to be 1; found {ar.ndim}")
            elif ar.shape != self.shape:
                raise ValueError(
                    f"expected '{name}' shape to be {self.shape}; found {ar.shape}"
                )
            setattr(self, name, ar)
        for name in int_any.keys():
            ar = int_any[name]
            if ar.ndim == 0:
                ar = np.full(self.shape, ar)
            elif ar.ndim != 1:
                raise ValueError(f"expected '{name}' ndim to be 1; found {ar.ndim}")
            elif ar.shape != self.shape:
                raise ValueError(
                    f"expected '{name}' shape to be {self.shape}; found {ar.shape}"
                )
            if not np.issubdtype(ar.dtype, np.integer):
                raise ValueError(
                    f"expected '{name}' to be integer type; found {ar.dtype}"
                )
            setattr(self, name, ar.astype(np.int32, copy=False))

    def __len__(self) -> int:
        """Return length of dimension from shape[0]."""
        return self.shape[0]

    def validate(self, name, **kwargs) -> None:
        """Validate array values.

        Parameters
        ----------
        name : str
            Name of parameter.
        kwargs : dict
            Supported validation keywords are: isfinite, gt, ge, lt, le, isin
            and enum.

        Raises
        ------
        ValueError
            When 1 or more array elements fail validation criteria.
        NotImplementedError
            When keyword is not recognized.
        """
        if name not in self._names:
            raise KeyError(f"'{name}' not found")
        ar = getattr(self, name)
        typ = ar.dtype.type
        if "isfinite" in kwargs:
            assert kwargs.pop("isfinite") is True
            if not np.isfinite(ar).all():
                raise ValueError(f"'{name}' must be finite")
        if "gt" in kwargs:
            gt = typ(kwargs.pop("gt"))
            if not (ar > gt).all():
                raise ValueError(f"'{name}' must be greater than {gt}")
        if "ge" in kwargs:
            ge = typ(kwargs.pop("ge"))
            if not (ar >= ge).all():
                raise ValueError(f"'{name}' must be greater than or equal to {ge}")
        if "lt" in kwargs:
            lt = typ(kwargs.pop("lt"))
            if not (ar < lt).all():
                raise ValueError(f"'{name}' must be less than {lt}")
        if "le" in kwargs:
            le = typ(kwargs.pop("le"))
            if not (ar <= le).all():
                raise ValueError(f"'{name}' must be less than or equal to {le}")
        if "isin" in kwargs:
            isin = kwargs.pop("isin")
            if not np.isin(ar, isin).all():
                raise ValueError(f"'{name}' must be in {isin}")
        if "enum" in kwargs:
            enum_v = kwargs.pop("enum")
            valid_options = enum_v.get_valid_options()
            if not np.isin(ar, list(valid_options.keys())).all():
                enum_str = ", ".join([f"{v} ({n})" for (v, n) in valid_options.items()])
                raise ValueError(f"'{name}' must be in {enum_v}: {enum_str}")
        if kwargs:
            raise NotImplementedError(f"unhandled kwargs {kwargs}")
