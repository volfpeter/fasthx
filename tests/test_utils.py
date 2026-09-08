import inspect
import sys
from typing import TYPE_CHECKING

import pytest

from fasthx.utils import append_to_signature

if TYPE_CHECKING:

    class OnlyInTypeChecking:
        """Pretend type that is not available at runtime."""

        ...


def test_append_to_signature_with_string_annotations() -> None:
    # Quoted annotations fail to resolve in `eval_str` mode but are kept as
    # strings on every supported Python version, leaving their resolution
    # to the caller (FastAPI resolves string annotations).
    def source(value: "OnlyInTypeChecking") -> "OnlyInTypeChecking":
        raise NotImplementedError

    extra = inspect.Parameter("extra", inspect.Parameter.KEYWORD_ONLY, default=1)
    result = append_to_signature(source, extra)

    signature = inspect.signature(result)
    assert list(signature.parameters) == ["value", "extra"]
    assert signature.parameters["value"].annotation == "OnlyInTypeChecking"
    assert signature.return_annotation == "OnlyInTypeChecking"


@pytest.mark.skipif(sys.version_info < (3, 14), reason="Requires lazy (PEP 649) annotations.")
def test_append_to_signature_with_type_checking_annotations() -> None:
    # Unquoted annotations are lazily evaluated on 3.14+ and can only fail
    # when the signature is inspected; unresolvable ones come back as
    # forward references that FastAPI can resolve or ignore.
    def source(value: OnlyInTypeChecking) -> OnlyInTypeChecking:
        raise NotImplementedError

    extra = inspect.Parameter("extra", inspect.Parameter.KEYWORD_ONLY, default=1)
    result = append_to_signature(source, extra)

    signature = inspect.signature(result)
    assert list(signature.parameters) == ["value", "extra"]
    assert signature.parameters["value"].annotation.__forward_arg__ == "OnlyInTypeChecking"
    assert signature.return_annotation.__forward_arg__ == "OnlyInTypeChecking"
