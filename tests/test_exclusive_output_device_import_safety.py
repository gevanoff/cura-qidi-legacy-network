import ast
from pathlib import Path


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "cura_plugin"
    / "QidiLegacyNetwork"
    / "exclusive_output_device.py"
)


def _exclusive_class() -> ast.ClassDef:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "ExclusiveQidiLegacyOutputDevice"
    )


def test_exclusive_device_does_not_add_a_second_pyqt_property_layer() -> None:
    """Keep Cura's wrapped output-device meta-object defined by the working base class."""

    cls = _exclusive_class()
    decorators = [
        decorator
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for decorator in node.decorator_list
    ]

    assert not any(
        isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Name)
        and decorator.func.id == "pyqtProperty"
        for decorator in decorators
    )


def test_qt_base_constructor_runs_before_instance_state_assignment() -> None:
    """Do not touch the wrapped QObject instance before its base constructor runs."""

    cls = _exclusive_class()
    init = next(
        node
        for node in cls.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )

    super_call_index = next(
        index
        for index, statement in enumerate(init.body)
        if isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Call)
        and isinstance(statement.value.func, ast.Attribute)
        and statement.value.func.attr == "__init__"
        and isinstance(statement.value.func.value, ast.Call)
        and isinstance(statement.value.func.value.func, ast.Name)
        and statement.value.func.value.func.id == "super"
    )
    state_assignment_index = next(
        index
        for index, statement in enumerate(init.body)
        if isinstance(statement, ast.Assign)
        and any(
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
            and target.attr == "_communication_state"
            for target in statement.targets
        )
    )

    assert super_call_index < state_assignment_index
